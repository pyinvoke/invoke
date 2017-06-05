import copy
import inspect
import json
import os
from os.path import join, splitext, expanduser

try:
    from .vendor import six
    if six.PY3:
        from .vendor import yaml3 as yaml
    else:
        from .vendor import yaml2 as yaml
except ImportError:
    # Use system modules
    import six
    import yaml

if six.PY3:
    try:
        from importlib.machinery import SourceFileLoader
    except ImportError: # PyPy3
        from importlib._bootstrap import _SourceFileLoader as SourceFileLoader
    def load_source(name, path):
        if not os.path.exists(path):
            return {}
        return vars(SourceFileLoader('mod', path).load_module())
else:
    import imp
    def load_source(name, path):
        if not os.path.exists(path):
            return {}
        return vars(imp.load_source('mod', path))

from .env import Environment
from .exceptions import UnknownFileType
from .platform import WINDOWS
from .runners import Local
from .util import debug


class DataProxy(object):
    """
    Helper class implementing nested dict+attr access for `.Config`.

    Specifically, is used both for `.Config` itself, and to wrap any other
    dicts assigned as config values (recursively).

    .. warning::
        All methods (of this object or in subclasses) must take care to
        initialize new attributes via ``self._set(name='value')``, or they'll
        run into recursion errors!
    """
    # Attributes which get proxied through to inner merged-dict config obj.
    _proxies = tuple("""
        get
        has_key
        items
        iteritems
        iterkeys
        itervalues
        keys
        values
    """.split()) + tuple("__{0}__".format(x) for x in """
        cmp
        contains
        iter
        sizeof
    """.split())

    @classmethod
    def from_data(cls, data, root=None, keypath=None):
        """
        Alternate constructor for 'baby' DataProxies used as sub-dict values.

        Allows creating standalone DataProxy objects while also letting
        subclasses like `.Config` define their own ``__init__`` without
        muddling the two.

        :param dict data:
            This particular DataProxy's personal data. Required, it's the Data
            being Proxied.

        :param root:
            Optional handle on a root DataProxy/Config which needs notification
            on data updates.

        :param tuple keypath:
            Optional tuple describing the path of keys leading to this
            DataProxy's location inside the ``root`` structure. Required if
            ``root`` was given (and vice versa.)
        """
        obj = cls()
        obj._set(_config=data)
        obj._set(_root=root)
        if keypath is None:
            keypath = tuple()
        obj._set(_keypath=keypath)
        return obj

    def __getattr__(self, key):
        # NOTE: due to default Python attribute-lookup semantics, "real"
        # attributes will always be yielded on attribute access and this method
        # is skipped. That behavior is good for us (it's more intuitive than
        # having a config key accidentally shadow a real attribute or method).
        try:
            return self._get(key)
        except KeyError:
            # Proxy most special vars to config for dict procotol.
            if key in self._proxies:
                return getattr(self._config, key)
            # Otherwise, raise useful AttributeError to follow getattr proto.
            err = "No attribute or config key found for {0!r}".format(key)
            attrs = [x for x in dir(self.__class__) if not x.startswith('_')]
            err += "\n\nValid keys: {0!r}".format(
                sorted(list(self._config.keys()))
            )
            err += "\n\nValid real attributes: {0!r}".format(attrs)
            raise AttributeError(err)

    def __setattr__(self, key, value):
        # Turn attribute-sets into config updates anytime we don't have a real
        # attribute with the given name/key.
        has_real_attr = key in (x[0] for x in inspect.getmembers(self))
        if not has_real_attr:
            # Make sure to trigger our own __setitem__ instead of going direct
            # to our internal dict/cache
            self[key] = value
        else:
            super(DataProxy, self).__setattr__(key, value)

    def __iter__(self):
        # For some reason Python is ignoring our __hasattr__ when determining
        # whether we support __iter__. BOO
        return iter(self._config)

    def __eq__(self, other):
        # NOTE: Can't proxy __eq__ because the RHS will always be an obj of the
        # current class, not the proxied-to class, and that causes
        # NotImplemented.
        # Try comparing to other objects like ourselves, falling back to a not
        # very comparable value (None) so comparison fails.
        other_val = getattr(other, '_config', None)
        # But we can compare to vanilla dicts just fine, since our _config is
        # itself just a dict.
        if isinstance(other, dict):
            other_val = other
        return self._config == other_val

    # Make unhashable, because our entire raison d'etre is to be somewhat
    # mutable. Subclasses with mutable attributes may override this.
    # NOTE: this is mostly a concession to Python 2, v3 does it automatically.
    __hash__ = None

    def __len__(self):
        return len(self._config)

    def __setitem__(self, key, value):
        self._config[key] = value
        self._track_modification_of(key, value)

    def __getitem__(self, key):
        return self._get(key)

    def _get(self, key):
        # Short-circuit if pickling/copying mechanisms are asking if we've got
        # __setstate__ etc; they'll ask this w/o calling our __init__ first, so
        # we'd be in a RecursionError-causing catch-22 otherwise.
        if key in (
            '__setstate__',
        ):
            raise AttributeError(key)
        # At this point we should be able to assume a self._config...
        value = self._config[key]
        if isinstance(value, dict):
            # New object's keypath is simply the key, prepended with our own
            # keypath if we've got one.
            keypath = (key,)
            if hasattr(self, '_keypath'):
                keypath = self._keypath + keypath
            # If we have no _root, we must be the root, so it's us. Otherwise,
            # pass along our handle on the root.
            root = getattr(self, '_root', self)
            value = DataProxy.from_data(
                data=value,
                root=root,
                keypath=keypath,
            )
        return value

    def _set(self, *args, **kwargs):
        """
        Convenience workaround of default 'attrs are config keys' behavior.

        Uses `object.__setattr__` to work around the class' normal proxying
        behavior, but is less verbose than using that directly.

        Has two modes (which may be combined if you really want):

        - ``self._set('attrname', value)``, just like ``__setattr__``
        - ``self._set(attname=value)`` (i.e. kwargs), even less typing.
        """
        if args:
            object.__setattr__(self, *args)
        for key, value in six.iteritems(kwargs):
            object.__setattr__(self, key, value)

    def __repr__(self):
        return "<{0}: {1}>".format(self.__class__.__name__, self._config)

    def __contains__(self, key):
        return key in self._config

    @property
    def _is_leaf(self):
        return hasattr(self, '_root')

    @property
    def _is_root(self):
        return hasattr(self, '_modify')

    def _track_removal_of(self, key):
        # Grab the root object responsible for tracking removals; either the
        # referenced root (if we're a leaf) or ourselves (if we're not).
        # (Intermediate nodes never have anything but __getitem__ called on
        # them, otherwise they're by definition being treated as a leaf.)
        target = None
        if self._is_leaf:
            target = self._root
        elif self._is_root:
            target = self
        if target is not None:
            target._remove(getattr(self, '_keypath', tuple()), key)

    def _track_modification_of(self, key, value):
        target = None
        if self._is_leaf:
            target = self._root
        elif self._is_root:
            target = self
        if target is not None:
            target._modify(getattr(self, '_keypath', tuple()), key, value)

    def __delitem__(self, key):
        del self._config[key]
        self._track_removal_of(key)

    def __delattr__(self, name):
        # Make sure we don't screw up true attribute deletion for the
        # situations that actually want it. (Uncommon, but not rare.)
        if name in self:
            del self[name]
        else:
            object.__delattr__(self, name)

    def clear(self):
        keys = list(self.keys())
        for key in keys:
            del self[key]

    def pop(self, *args):
        # Must test this up front before (possibly) mutating self._config
        key_existed = args and args[0] in self._config
        # We always have a _config (whether it's a real dict or a cache of
        # merged levels) so we can fall back to it for all the corner case
        # handling re: args (arity, handling a default, raising KeyError, etc)
        ret = self._config.pop(*args)
        # If it looks like no popping occurred (key wasn't there), presumably
        # user gave default, so we can short-circuit return here - no need to
        # track a deletion that did not happen.
        if not key_existed:
            return ret
        # Here, we can assume at least the 1st posarg (key) existed.
        self._track_removal_of(args[0])
        # In all cases, return the popped value.
        return ret

    def popitem(self):
        ret = self._config.popitem()
        self._track_removal_of(ret[0])
        return ret

    def setdefault(self, *args):
        # Must test up front whether the key existed beforehand
        key_existed = args and args[0] in self._config
        # Run locally
        ret = self._config.setdefault(*args)
        # Key already existed -> nothing was mutated, short-circuit
        if key_existed:
            return ret
        # Here, we can assume the key did not exist and thus user must have
        # supplied a 'default' (if they did not, the real setdefault() above
        # would have excepted.)
        key, default = args
        self._track_modification_of(key, default)
        return ret

    def update(self, *args, **kwargs):
        if kwargs:
            for key, value in six.iteritems(kwargs):
                self[key] = value
        elif args:
            # TODO: complain if arity>1
            arg = args[0]
            if isinstance(arg, dict):
                for key in arg:
                    self[key] = arg[key]
            else:
                # TODO: be stricter about input in this case
                for pair in arg:
                    self[pair[0]] = pair[1]


class Config(DataProxy):
    """
    Invoke's primary configuration handling class.

    See :doc:`/concepts/configuration` for details on the configuration system
    this class implements, including the :ref:`configuration hierarchy
    <config-hierarchy>`. The rest of this class' documentation assumes
    familiarity with that document.

    **Access**

    Configuration values may be accessed and/or updated using dict syntax::

        config['foo']

    or attribute syntax::

        config.foo

    Nesting works the same way - dict config values are turned into objects
    which honor both the dictionary protocol and the attribute-access method::

       config['foo']['bar']
       config.foo.bar

    **A note about attribute access and methods**

    This class implements the entire dictionary protocol: methods such as
    ``keys``, ``values``, ``items``, ``pop`` and so forth should all function
    as they do on regular dicts. It also implements new config-specific methods
    such as `.load_files`, `.load_collection` and `.clone`.

    .. warning::
        Accordingly, this means that if you have configuration options sharing
        names with these methods, you **must** use dictionary syntax (e.g.
        ``myconfig['keys']``) to access the configuration data.

    **Lifecycle**

    At initialization time, `.Config`:

    - creates per-level data structures
    - stores levels supplied to `__init__`, such as defaults or overrides, as
      well as the various config file paths/prefixes
    - loads system, user and project level config files, if found

    At this point, `.Config` is fully usable, but in most real-world use cases,
    the CLI machinery (or library users) do additional work on a per-task
    basis:

    - the result of CLI argument parsing is applied to the overrides level
    - a runtime config file is loaded, if its flag was supplied
    - the base config is cloned (so tasks don't inadvertently affect one
      another)
    - per-collection data is loaded (only possible now that we have a task in
      hand)
    - shell environment data is loaded (must be done at end of process due to
      using the rest of the config as a guide for interpreting env var names)

    Any modifications made directly to the `.Config` itself (usually, after it
    has been handed to the task or other end-user code) end up stored in their
    own (topmost) config level, making it easy to debug final values.

    Finally, any *deletions* made to the `.Config` (e.g. applications of
    dict-style mutators like ``pop``, ``clear`` etc) are tracked in their own
    structure, allowing the overall object to honor such method calls despite
    the source data itself not changing.

    **Special class attributes**

    The following class-level attributes are used for low-level configuration
    of the config system itself, such as which file paths to load. They are
    primarily intended for overriding by subclasses.

    - ``prefix``: Supplies the default value for ``file_prefix`` (directly) and
      ``env_prefix`` (uppercased). See their descriptions for details. Its
      default value is ``"invoke"``.
    - ``file_prefix``: The config file 'basename' default (though it is not a
      literal basename; it can contain path parts if desired) which is appended
      to the configured values of ``system_prefix``, ``user_prefix``, etc, to
      arrive at the final (pre-extension) file paths.

      Thus, by default, a system-level config file path concatenates the
      ``system_prefix`` of ``/etc/`` with the ``file_prefix`` of ``invoke`` to
      arrive at paths like ``/etc/invoke.json``.

      Defaults to ``None``, meaning to use the value of ``prefix``.

    - ``env_prefix``: A prefix used (along with a joining underscore) to
      determine which environment variables are loaded as the env var
      configuration level. Since its default is the value of ``prefix``
      capitalized, this means env vars like ``INVOKE_RUN_ECHO`` are sought by
      default.

      Defaults to ``None``, meaning to use the value of ``prefix``.
    """
    prefix = 'invoke'
    file_prefix = None
    env_prefix = None

    @staticmethod
    def global_defaults():
        """
        Return the core default settings for Invoke.

        Generally only for use by `.Config` internals. For descriptions of
        these values, see :ref:`default-values`.

        Subclasses may choose to override this method, calling
        ``Config.global_defaults`` and applying `.merge_dicts` to the result,
        to add to or modify these values.
        """
        return {
            # TODO: we document 'debug' but it's not truly implemented outside
            # of env var and CLI flag. If we honor it, we have to go around and
            # figure out at what points we might want to call
            # `util.enable_logging`:
            # - just using it as a fallback default for arg parsing isn't much
            # use, as at that point the config holds nothing but defaults & CLI
            # flag values
            # - doing it at file load time might be somewhat useful, though
            # where this happens may be subject to change soon
            # - doing it at env var load time seems a bit silly given the
            # existing support for at-startup testing for INVOKE_DEBUG
            # 'debug': False,
            # TODO: I feel like we want these to be more consistent re: default
            # values stored here vs 'stored' as logic where they are
            # referenced, there are probably some bits that are all "if None ->
            # default" that could go here. Alternately, make _more_ of these
            # default to None?
            'run': {
                'warn': False,
                'hide': None,
                'shell': '/bin/bash',
                'pty': False,
                'fallback': True,
                'env': {},
                'replace_env': False,
                'echo': False,
                'encoding': None,
                'out_stream': None,
                'err_stream': None,
                'in_stream': None,
                'watchers': [],
                'echo_stdin': None,
            },
            # This doesn't live inside the 'run' tree; otherwise it'd make it
            # somewhat harder to extend/override in Fabric 2 which has a split
            # local/remote runner situation.
            'runners': {
                'local': Local,
            },
            'sudo': {
                'prompt': "[sudo] password: ",
                'password': None,
                'user': None,
            },
            'tasks': {
                'dedupe': True,
            },
        }

    def __init__(
        self,
        overrides=None,
        defaults=None,
        system_prefix=None,
        user_prefix=None,
        project_home=None,
        runtime_path=None,
        defer_post_init=False,
    ):
        """
        Creates a new config object.

        :param dict defaults:
            A dict containing default (lowest level) config data. Default:
            `global_defaults`.

        :param dict overrides:
            A dict containing override-level config data. Default: ``{}``.

        :param str system_prefix:
            Base path for the global config file location; combined with the
            prefix and file suffixes to arrive at final file path candidates.

            Default: ``/etc/`` (thus e.g. ``/etc/invoke.yaml`` or
            ``/etc/invoke.json``).

        :param str user_prefix:
            Like ``system_prefix`` but for the per-user config file. These
            variables are joined as strings, not via path-style joins, so they
            may contain partial file paths; for the per-user config file this
            often means a leading dot, to make the final result a hidden file
            on most systems.

            Default: ``~/.`` (e.g. ``~/.invoke.yaml``).

        :param str project_home:
            Optional directory path location of the currently loaded
            `.Collection` (as loaded by `.Loader`). When non-empty, will
            trigger seeking of per-project config files in this location +
            ``invoke.(yaml|json|py)``.

        :param str runtime_path:
            Optional file path to a runtime configuration file.

            Used to fill the penultimate slot in the config hierarchy. Should
            be a full file path to an existing file, not a directory path, or a
            prefix.

        :param bool defer_post_init:
            Whether to defer certain steps at the end of `__init__`.

            Specifically, the `post_init` method is normally called
            automatically, and performs initial actions like loading config
            files. Advanced users may wish to call that method manually after
            manipulating the object; to do so, specify
            ``defer_post_init=True``.

            Default: ``False``.
        """
        # Technically an implementation detail - do not expose in public API.
        # Stores merged configs and is accessed via DataProxy.
        self._set(_config={})

        # Config file suffixes to search, in preference order.
        self._set(_file_suffixes=('yaml', 'yml', 'json', 'py'))

        # Default configuration values, typically a copy of `global_defaults`.
        if defaults is None:
            defaults = copy_dict(self.global_defaults())
        self._set(_defaults=defaults)

        # Collection-driven config data, gathered from the collection tree
        # containing the currently executing task.
        self._set(_collection={})

        # Path prefix searched for the system config file.
        # NOTE: There is no default system prefix on Windows.
        if system_prefix is None and not WINDOWS:
            system_prefix = '/etc/'
        self._set(_system_prefix=system_prefix)
        # Path to loaded system config file, if any.
        self._set(_system_path=None)
        # Whether the system config file has been loaded or not (or ``None`` if
        # no loading has been attempted yet.)
        self._set(_system_found=None)
        # Data loaded from the system config file.
        self._set(_system={})

        # Path prefix searched for per-user config files.
        if user_prefix is None:
            user_prefix = '~/.'
        self._set(_user_prefix=user_prefix)
        # Path to loaded user config file, if any.
        self._set(_user_path=None)
        # Whether the user config file has been loaded or not (or ``None`` if
        # no loading has been attempted yet.)
        self._set(_user_found=None)
        # Data loaded from the per-user config file.
        self._set(_user={})

        # Parent directory of the current root tasks file, if applicable.
        self._set(_project_home=project_home)
        # And a normalized prefix version not really publicly exposed
        project_prefix = None
        if self._project_home is not None:
            project_prefix = join(project_home, '')
        self._set(_project_prefix=project_prefix)
        # Path to loaded per-project config file, if any.
        self._set(_project_path=None)
        # Whether the project config file has been loaded or not (or ``None``
        # if no loading has been attempted yet.)
        self._set(_project_found=None)
        # Data loaded from the per-project config file.
        self._set(_project={})

        # Environment variable name prefix
        env_prefix = self.env_prefix
        if env_prefix is None:
            env_prefix = self.prefix
        env_prefix = "{0}_".format(env_prefix.upper())
        self._set(_env_prefix=env_prefix)
        # Config data loaded from the shell environment.
        self._set(_env={})

        # Path to the user-specified runtime config file.
        self._set(_runtime_path=runtime_path)
        # Data loaded from the runtime config file.
        self._set(_runtime={})
        # Whether the runtime config file has been loaded or not (or ``None``
        # if no loading has been attempted yet.)
        self._set(_runtime_found=None)

        # Overrides - highest normal config level. Typically filled in from
        # command-line flags.
        if overrides is None:
            overrides = {}
        self._set(_overrides=overrides)

        # Absolute highest level: user modifications.
        self._set(_modifications={})
        # And its sibling: user deletions. (stored as a flat dict of keypath
        # keys and dummy values, for constant-time membership testing/removal
        # w/ no messy recursion. TODO: maybe redo _everything_ that way? in
        # _modifications and other levels, the values would of course be
        # valuable and not just None)
        self._set(_deletions={})

        if not defer_post_init:
            self.post_init()

    def post_init(self):
        """
        Call setup steps that can occur immediately after `__init__`.

        May need to be manually called if `__init__` was told
        ``defer_post_init=True``.

        :returns: ``None``.
        """
        self.load_files()
        # TODO: just use a decorator for merging probably? shrug
        self.merge()

    def load_shell_env(self):
        """
        Load values from the shell environment.

        `.load_shell_env` is intended for execution late in a `.Config`
        object's lifecycle, once all other sources (such as a runtime config
        file or per-collection configurations) have been loaded. Loading from
        the shell is not terrifically expensive, but must be done at a specific
        point in time to ensure the "only known config keys are loaded from the
        env" behavior works correctly.

        See :ref:`env-vars` for details on this design decision and other info
        re: how environment variables are scanned and loaded.
        """
        # Force merge of existing data to ensure we have an up to date picture
        debug("Running pre-merge for shell env loading...")
        self.merge()
        debug("Done with pre-merge.")
        loader = Environment(config=self._config, prefix=self._env_prefix)
        self._set(_env=loader.load())
        debug("Loaded shell environment, triggering final merge")
        self.merge()

    def load_collection(self, data):
        """
        Update collection-driven config data.

        `.load_collection` is intended for use by the core task execution
        machinery, which is responsible for obtaining collection-driven data.
        See :ref:`collection-configuration` for details.
        """
        debug("Loading collection configuration")
        self._set(_collection=data)
        self.merge()

    def load_files(self):
        """
        Load any unloaded/un-searched-for config file sources.

        Specifically, any file sources whose ``_found`` values are ``None``
        will be sought and loaded if found; if their ``_found`` value is non
        ``None`` (e.g. ``True`` or ``False``) they will be skipped. Typically
        this means this method is idempotent and becomes a no-op after the
        first run.
        """
        self._load_file(prefix='system')
        self._load_file(prefix='user')
        self._load_file(prefix='project')
        self._load_file(prefix='runtime', absolute=True)

    def _load_file(self, prefix, absolute=False):
        # Setup
        found = "_{0}_found".format(prefix)
        path = "_{0}_path".format(prefix)
        data = "_{0}".format(prefix)
        midfix = self.file_prefix
        if midfix is None:
            midfix = self.prefix
        # Short-circuit if loading appears to have occurred already
        if getattr(self, found) is not None:
            return
        # Moar setup
        if absolute:
            absolute_path = getattr(self, path)
            # None -> expected absolute path but none set, short circuit
            if absolute_path is None:
                return
            paths = [absolute_path]
        else:
            path_prefix = getattr(self, "_{0}_prefix".format(prefix))
            # Short circuit if loading seems unnecessary (eg for project config
            # files when not running out of a project)
            if path_prefix is None:
                return
            paths = [
                '.'.join((path_prefix + midfix, x))
                for x in self._file_suffixes
            ]
        # Poke 'em
        for filepath in paths:
            # Normalize
            filepath = expanduser(filepath)
            try:
                try:
                    type_ = splitext(filepath)[1].lstrip('.')
                    loader = getattr(self, "_load_{0}".format(type_))
                except AttributeError as e:
                    msg = "Config files of type {0!r} (from file {1!r}) are not supported! Please use one of: {2!r}" # noqa
                    raise UnknownFileType(msg.format(
                        type_, filepath, self._file_suffixes))
                # Store data, the path it was found at, and fact that it was
                # found
                setattr(self, data, loader(filepath))
                setattr(self, path, filepath)
                setattr(self, found, True)
                break
            # Typically means 'no such file', so just note & skip past.
            except IOError as e:
                # TODO: is there a better / x-platform way to detect this?
                if "No such file" in e.strerror:
                    err = "Didn't see any {0}, skipping."
                    debug(err.format(filepath))
                else:
                    raise
        # Still None -> no suffixed paths were found, record this fact
        if getattr(self, path) is None:
            setattr(self, found, False)

    def _load_yaml(self, path):
        with open(path) as fd:
            return yaml.load(fd)

    def _load_yml(self, path):
        return self._load_yaml(path)

    def _load_json(self, path):
        with open(path) as fd:
            return json.load(fd)

    def _load_py(self, path):
        data = {}
        for key, value in six.iteritems(load_source('mod', path)):
            if key.startswith('__'):
                continue
            data[key] = value
        return data

    @property
    def paths(self):
        """
        An iterable of all successfully loaded config file paths.

        No specific order.
        """
        paths = []
        for prefix in "system user project runtime".split():
            value = getattr(self, "_{0}_path".format(prefix))
            if value is not None:
                paths.append(value)
        return paths

    def merge(self):
        """
        Merge all config sources, in order.
        """
        debug("Merging config sources in order onto new empty _config...")
        self._config = {}
        debug("Defaults: {0!r}".format(self._defaults))
        merge_dicts(self._config, self._defaults)
        debug("Collection-driven: {0!r}".format(self._collection))
        merge_dicts(self._config, self._collection)
        self._merge_file('system', "System-wide")
        self._merge_file('user', "Per-user")
        self._merge_file('project', "Per-project")
        debug("Environment variable config: {0!r}".format(self._env))
        merge_dicts(self._config, self._env)
        self._merge_file('runtime', "Runtime")
        debug("Overrides: {0!r}".format(self._overrides))
        merge_dicts(self._config, self._overrides)
        debug("Modifications: {0!r}".format(self._modifications))
        merge_dicts(self._config, self._modifications)
        debug("Deletions: {0!r}".format(self._deletions))
        obliterate(self._config, self._deletions)

    def _merge_file(self, name, desc):
        # Setup
        desc += " config file" # yup
        found = getattr(self, "_{0}_found".format(name))
        path = getattr(self, "_{0}_path".format(name))
        data = getattr(self, "_{0}".format(name))
        # None -> no loading occurred yet
        if found is None:
            debug("{0} has not been loaded yet, skipping".format(desc))
        # True -> hooray
        elif found:
            debug("{0} ({1}): {2!r}".format(desc, path, data))
            merge_dicts(self._config, data)
        # False -> did try, did not succeed
        else:
            # TODO: how to preserve what was tried for each case but only for
            # the negative? Just a branch here based on 'name'?
            debug("{0} not found, skipping".format(desc))

    def clone(self, into=None):
        """
        Return a copy of this configuration object.

        The new object will be identical in terms of configured sources and any
        loaded (or user-manipulated) data, but will be a distinct object with
        as little shared mutable state as possible.

        Specifically, all `dict` values within the config are recursively
        recreated, with non-dict leaf values subjected to `copy.copy` (note:
        *not* `copy.deepcopy`, as this can cause issues with various objects
        such as compiled regexen or threading locks, often found buried deep
        within rich aggregates like API or DB clients).

        The only remaining config values that may end up shared between a
        config and its clone are thus those 'rich' objects that do not
        `copy.copy` cleanly, or compound non-dict objects (such as lists or
        tuples).

        :param into:
            A `.Config` subclass that the new clone should be "upgraded" to.

            Used by client libraries which have their own `.Config` subclasses
            that e.g. define additional defaults; cloning "into" one of these
            subclasses ensures that any new keys/subtrees are added gracefully,
            without overwriting anything that may have been pre-defined.

            Default: ``None`` (just clone into another regular `.Config`).

        :returns:
            A `.Config`, or an instance of the class given to ``into``.

        :raises:
            ``TypeError``, if ``into`` is given a value and that value is not a
            `.Config` subclass.
        """
        # Sanity check for 'into'
        if into is not None and not issubclass(into, self.__class__):
            err = "'into' must be a subclass of {0}!"
            raise TypeError(err.format(self.__class__.__name__))
        # Construct new object
        klass = self.__class__ if into is None else into
        # Also allow arbitrary constructor kwargs, for subclasses where passing
        # (some) data in at init time is desired (vs post-init copying)
        # TODO: probably want to pivot the whole class this way eventually...?
        # No longer recall exactly why we went with the 'fresh init + attribute
        # setting' approach originally...tho there's clearly some impedance
        # mismatch going on between "I want stuff to happen in my config's
        # instantiation" and "I want cloning to not trigger certain things like
        # external data source loading".
        # NOTE: this will include defer_post_init, see end of method
        new = klass(**self._clone_init_kwargs(into=into))
        # Copy/merge/etc all 'private' data sources and attributes
        for name in """
            collection
            system_prefix
            system_path
            system_found
            system
            user_prefix
            user_path
            user_found
            user
            project_home
            project_prefix
            project_path
            project_found
            project
            env_prefix
            env
            runtime_path
            runtime_found
            runtime
            overrides
            modifications
        """.split():
            name = "_{0}".format(name)
            my_data = getattr(self, name)
            # Non-dict data gets carried over straight (via a copy())
            # NOTE: presumably someone could really screw up and change these
            # values' types, but at that point it's on them...
            if not isinstance(my_data, dict):
                setattr(new, name, copy.copy(my_data))
            # Dict data gets merged (which also involves a copy.copy
            # eventually)
            else:
                merge_dicts(getattr(new, name), my_data)
        # And merge the central config too (cannot just call .merge() on the
        # new clone, since the source config may have received custom
        # alterations by user code.)
        merge_dicts(new._config, self._config)
        # Finally, call new.post_init() since it's fully merged up. This way,
        # stuff called in post_init() will have access to the final version of
        # the data.
        new.post_init()
        return new

    def _clone_init_kwargs(self, into=None):
        """
        Supply kwargs suitable for initializing a new clone of this object.

        Note that most of the `.clone` process involves copying data between
        two instances instead of passing init kwargs; however, sometimes you
        really do want init kwargs, which is why this method exists.

        :param into: The value of ``into`` as passed to the calling `.clone`.

        :returns: A `dict`.
        """
        # NOTE: must pass in defaults fresh or otherwise global_defaults() gets
        # used instead. Except when 'into' is in play, in which case we truly
        # want the union of the two.
        new_defaults = copy_dict(self._defaults)
        if into is not None:
            merge_dicts(new_defaults, into.global_defaults())
        # The kwargs.
        return dict(
            defaults=new_defaults,
            # TODO: consider making this 'hardcoded' on the calling end (ie
            # inside clone()) to make sure nobody accidentally nukes it via
            # subclassing?
            defer_post_init=True,
        )

    def _modify(self, keypath, key, value):
        """
        Update our user-modifications config level with new data.

        :param tuple keypath:
            The key path identifying the sub-dict being updated. May be an
            empty tuple if the update is occurring at the topmost level.

        :param str key:
            The actual key receiving an update.

        :param value:
            The value being written.
        """
        # First, ensure we wipe the keypath from _deletions, in case it was
        # previously deleted.
        excise(self._deletions, keypath + (key,))
        # Now we can add it to the modifications structure.
        data = self._modifications
        keypath = list(keypath)
        while keypath:
            subkey = keypath.pop(0)
            # TODO: could use defaultdict here, but...meh?
            if subkey not in data:
                # TODO: generify this and the subsequent 3 lines...
                data[subkey] = {}
            data = data[subkey]
        data[key] = value
        self.merge()

    def _remove(self, keypath, key):
        """
        Like `._modify`, but for removal.
        """
        # NOTE: because deletions are processed in merge() last, we do not need
        # to remove things from _modifications on removal; but we *do* do the
        # inverse - remove from _deletions on modification.
        # TODO: may be sane to push this step up to callers?
        data = self._deletions
        keypath = list(keypath)
        while keypath:
            subkey = keypath.pop(0)
            if subkey in data:
                data = data[subkey]
                # If we encounter None, it means something higher up than our
                # requested keypath is already marked as deleted; so we don't
                # have to do anything or go further.
                if data is None:
                    return
                # Otherwise it's presumably another dict, so keep looping...
            else:
                # Key not found -> nobody's marked anything along this part of
                # the path for deletion, so we'll start building it out.
                data[subkey] = {}
                # Then prep for next iteration
                data = data[subkey]
        # Exited loop -> data must be the leafmost dict, so we can now set our
        # deleted key to None
        data[key] = None
        self.merge()


class AmbiguousMergeError(ValueError):
    pass


def merge_dicts(base, updates):
    """
    Recursively merge dict ``updates`` into dict ``base`` (mutating ``base``.)

    * Values which are themselves dicts will be recursed into.
    * Values which are a dict in one input and *not* a dict in the other input
      (e.g. if our inputs were ``{'foo': 5}`` and ``{'foo': {'bar': 5}}``) are
      irreconciliable and will generate an exception.
    * Non-dict leaf values are run through `copy.copy` to avoid state bleed.

    .. note::
        This is effectively a lightweight `copy.deepcopy` which offers
        protection from mismatched types (dict vs non-dict) and avoids some
        core deepcopy problems (such as how it explodes on certain object
        types).

    :returns:
        The value of ``base``, which is mostly useful for wrapper functions
        like `copy_dict`.
    """
    # TODO: for chrissakes just make it return instead of mutating?
    for key, value in updates.items():
        # Dict values whose keys also exist in 'base' -> recurse
        # (But only if both types are dicts.)
        if key in base:
            if isinstance(value, dict):
                if isinstance(base[key], dict):
                    merge_dicts(base[key], value)
                else:
                    raise _merge_error(base[key], value)
            else:
                if isinstance(base[key], dict):
                    raise _merge_error(base[key], value)
                else:
                    base[key] = copy.copy(value)
        # New values get set anew
        else:
            # Dict values get reconstructed to avoid being references to the
            # updates dict, which can lead to nasty state-bleed bugs otherwise
            if isinstance(value, dict):
                base[key] = copy_dict(value)
            # Non-dict values just get set straight
            else:
                base[key] = copy.copy(value)
    return base

def _merge_error(orig, new_):
    return AmbiguousMergeError("Can't cleanly merge {0} with {1}".format(
        _format_mismatch(orig), _format_mismatch(new_)
    ))

def _format_mismatch(x):
    return "{0} ({1!r})".format(type(x), x)


def copy_dict(source):
    """
    Return a fresh copy of ``source`` with as little shared state as possible.

    Uses `merge_dicts` under the hood, with an empty ``base`` dict; see its
    documentation for details on behavior.
    """
    return merge_dicts({}, source)


def excise(dict_, keypath):
    """
    Remove key pointed at by ``keypath`` from nested dict ``dict_``, if exists.
    """
    data = dict_
    keypath = list(keypath)
    leaf_key = keypath.pop()
    while keypath:
        key = keypath.pop(0)
        if key not in data:
            # Not there, nothing to excise
            return
        data = data[key]
    if leaf_key in data:
        del data[leaf_key]


def obliterate(base, deletions):
    """
    Remove all (nested) keys mentioned in ``deletions``, from ``base``.
    """
    for key, value in six.iteritems(deletions):
        if isinstance(value, dict):
            # NOTE: not testing for whether base[key] exists; if something's
            # listed in a deletions structure, it must exist in some source
            # somewhere, and thus also in the cache being obliterated.
            obliterate(base[key], deletions[key])
        else: # implicitly None
            del base[key]
