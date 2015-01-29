import copy
import imp
import json
import os
from os.path import join, splitext, expanduser

from .vendor import six
if six.PY3:
    from .vendor import yaml3 as yaml
else:
    from .vendor import yaml2 as yaml

from .env import Environment
from .exceptions import UnknownFileType
from .util import debug


class DataProxy(object):
    """
    Helper class implementing nested dict+attr access for `.Config`.
    """

    # Attributes which get proxied through to inner etc.Config obj.
    _proxies = tuple("""
        clear
        get
        has_key
        items
        iteritems
        iterkeys
        itervalues
        keys
        pop
        popitem
        setdefault
        update
        values
    """.split()) + tuple("__{0}__".format(x) for x in """
        cmp
        contains
        iter
        sizeof
    """.split())

    # Alt constructor used so we aren't getting in the way of Config's real
    # __init__().
    @classmethod
    def from_data(cls, data):
        obj = cls()
        obj.config = data
        return obj

    def __getattr__(self, key):
        try:
            return self._get(key)
        except KeyError:
            # Proxy most special vars to config for dict procotol.
            if key in self._proxies:
                return getattr(self.config, key)
            # Otherwise, raise useful AttributeError to follow getattr proto.
            err = "No attribute or config key found for {0!r}".format(key)
            attrs = [x for x in dir(self.__class__) if not x.startswith('_')]
            err += "\n\nValid keys: {0!r}".format(list(self.config.keys()))
            err += "\n\nValid real attributes: {0!r}".format(attrs)
            raise AttributeError(err)

    def __hasattr__(self, key):
        return key in self.config or key in self._proxies

    def __iter__(self):
        # For some reason Python is ignoring our __hasattr__ when determining
        # whether we support __iter__. BOO
        return iter(self.config)

    def __eq__(self, other):
        # Can't proxy __eq__ because the RHS will always be an obj of the
        # current class, not the proxied-to class, and that causes
        # NotImplemented.
        return self.config == other.config

    def __len__(self):
        # Can't proxy __len__ either apparently? ugh
        return len(self.config)

    def __setitem__(self, key, value):
        # ... or __setitem__? thanks for nothing Python >:(
        self.config[key] = value

    def __delitem__(self, key):
        # OK this is really getting annoying
        del self.config[key]

    def __getitem__(self, key):
        return self._get(key)

    def _get(self, key):
        value = self.config[key]
        if isinstance(value, dict):
            value = DataProxy.from_data(value)
        return value

    def __str__(self):
        return str(self.config)

    def __unicode__(self):
        return unicode(self.config)

    def __repr__(self):
        return repr(self.config)

    def __contains__(self, key):
        return key in self.config

    # TODO: copy()?


class Config(DataProxy):
    """
    Invoke's primary configuration handling class.

    See :doc:`/concepts/configuration` for details on the configuration system
    this class implements, including the :ref:`configuration hierarchy
    <config-hierarchy>`. The rest of this class' documentation assumes
    familiarity with that document.

    **Access**

    Configuration values may be accessed using dict syntax::

        config['foo']

    or attribute syntax::

        config.foo

    .. warning::
        Any "real" attributes (methods, etc) on `.Config` take precedence over
        settings values - so if you have top level settings named ``clone``,
        ``defaults``, etc, you *must* use dict syntax to access it.

    Nesting works the same way - dict config values are turned into objects
    which honor both the dictionary protocol and the attribute-access method::

       config['foo']['bar']
       config.foo.bar

    **Non-data attributes & methods**

    This class implements the entire dictionary protocol: methods such as
    ``keys``, ``values``, ``items``, ``pop`` and so forth should all function
    as they do on regular dicts.

    Individual configuration 'levels' and their source locations (if
    applicable) may be accessed via attributes such as
    `.project`/`.project_path` and so forth - see the documentation for
    individual members below for details.

    **Lifecycle**

    On initialization, `.Config` will seek out and load various configuration
    files from disk, then `.merge` the results with other in-memory sources
    such as defaults and CLI overrides.

    Typically, the `.load_collection` and `.load_shell_env` methods are called
    after initialization - `.load_collection` prior to each task invocation
    (because collection-level config data may change depending on the task) and
    `.load_shell_env` as the final step (as it needs the rest of the config to
    know which env vars are valid to load).

    Once users are given a copy of the configuration (usually via their task's
    `.Context` argument) all the above loading (& a final `.merge`) has been
    performed and they are free to modify it as they would any other regular
    dictionary.

    .. warning::
        Calling `.merge` after manually modifying `.Config` objects may
        overwrite those manual changes, since it overwrites the core config
        dict with data from per-source attributes like `.defaults` or `.user`.
    """

    def __init__(self, defaults=None, overrides=None, system_prefix=None,
        user_prefix=None, project_home=None, env_prefix=None,
        runtime_path=None):
        """
        Creates a new config object.

        :param dict defaults:
            A dict containing default (lowest level) config data. Default:
            ``{}``.

        :param dict overrides:
            A dict containing override-level config data. Default: ``{}``.

        :param str system_prefix:
            Path & partial filename for the global config file location. Should
            include everything but the dot & file extension.
            
            Default: ``/etc/invoke`` (e.g. ``/etc/invoke.yaml`` or
            ``/etc/invoke.json``).

        :param str user_prefix:
            Like ``system_prefix`` but for the per-user config file.

            Default: ``~/.invoke`` (e.g. ``~/.invoke.yaml``).

        :param str project_home:
            Optional directory path location of the currently loaded
            `.Collection` (as loaded by `.Loader`). When non-empty, will
            trigger seeking of per-project config files in this location +
            ``invoke.(yaml|json|py)``.

        :param str env_prefix:
            Environment variable seek prefix; optional, defaults to ``None``.

            When not ``None``, only environment variables beginning with this
            value will be loaded. If it is set, the keys will have the prefix
            stripped out before processing, so e.g. ``env_prefix='INVOKE_'``
            means users must set ``INVOKE_MYSETTING`` in the shell to affect
            the ``"mysetting"`` setting.

        :param str runtime_path:
            Optional file path to a runtime configuration file.

            Used to fill the penultimate slot in the config hierarchy. Should
            be a full file path to an existing file, not a directory path, or a
            prefix.
        """
        # Config file suffixes to search, in preference order.
        self.file_suffixes = ('yaml', 'json', 'py')

        # Technically an implementation detail - do not expose in public API.
        # Stores merged configs and is accessed via DataProxy.
        self.config = {}

        #: Default configuration values, typically hardcoded in the
        #: CLI/execution machinery.
        self.defaults = {} if defaults is None else defaults

        #: Collection-driven config data, gathered from the collection tree
        #: containing the currently executing task.
        self.collection = {}

        #: Path prefix searched for the system config file.
        self.system_prefix = ('/etc/invoke' if system_prefix is None
            else system_prefix)
        #: Path to loaded system config file, if any.
        self.system_path = None
        #: Whether the system config file has been loaded or not (or ``None``
        #: if no loading has been attempted yet.)
        self.system_found = None
        #: Data loaded from the system config file.
        self.system = {}

        #: Path prefix searched for per-user config files.
        self.user_prefix = '~/.invoke' if user_prefix is None else user_prefix
        #: Path to loaded user config file, if any.
        self.user_path = None
        #: Whether the user config file has been loaded or not (or ``None``
        #: if no loading has been attempted yet.)
        self.user_found = None
        #: Data loaded from the per-user config file.
        self.user = {}

        #: Parent directory of the current root tasks file, if applicable.
        self.project_home = project_home
        # And a normalized prefix version not really publicly exposed
        self.project_prefix = None
        if self.project_home is not None:
            self.project_prefix = join(project_home, 'invoke')
        #: Path to loaded per-project config file, if any.
        self.project_path = None
        #: Whether the project config file has been loaded or not (or ``None``
        #: if no loading has been attempted yet.)
        self.project_found = None
        #: Data loaded from the per-project config file.
        self.project = {}

        #: Environment variable name prefix
        # TODO: make this INVOKE_ and update tests to account?
        self.env_prefix = '' if env_prefix is None else env_prefix
        #: Config data loaded from the shell environment.
        self.env = {}

        #: Path to the user-specified runtime config file.
        self.runtime_path = runtime_path
        #: Data loaded from the runtime config file.
        self.runtime = {}
        #: Whether the runtime config file has been loaded or not (or ``None``
        #: if no loading has been attempted yet.)
        self.runtime_found = None

        #: Overrides - highest possible config level. Typically filled in from
        #: command-line flags.
        self.overrides = {} if overrides is None else overrides

        # Perform initial load & merge.
        self.load_files()
        self.merge()

    def load_shell_env(self):
        """
        Load values from the shell environment.

        `.load_shell_env` is intended for execution late in a `.Config`
        object's lifecycle, once all other sources have been merged. Loading
        from the shell is not terrifically expensive, but must be done at a
        specific point in time to ensure the "only known config keys are loaded
        from the env" behavior works correctly.
        
        See :ref:`env-vars` for details on this design decision and other info
        re: how environment variables are scanned and loaded.
        """
        # Force merge of existing data to ensure we have an up to date picture
        debug("Running pre-merge for shell env loading...")
        self.merge()
        debug("Done with pre-merge.")
        loader = Environment(config=self.config, prefix=self.env_prefix)
        self.env = loader.load()
        debug("Loaded shell environment, triggering final merge")
        self.merge()

    def load_collection(self, data):
        """
        Update collection-driven config data.

        `.load_collection` is intended for use by the core task execution
        machinery, which is responsible for obtaining per-task
        collection-driven data. See :ref:`collection-configuration` for
        details.

        .. note:: This method triggers `.merge` after it runs.
        """
        self.collection = data
        self.merge()

    def clone(self):
        """
        Return a copy of this configuration object.

        The new object will be identical in terms of configured sources and any
        loaded/merged data, but will be a distinct object with no shared
        mutable state.
        """
        new = Config()
        for name in """
            config
            defaults
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
        """.split():
            setattr(new, name, copy.deepcopy(getattr(self, name)))
        return new

    def load_files(self):
        """
        Load any unloaded/un-searched-for config file sources.

        Specifically, any file sources whose ``_found`` values are ``None``
        will be sought and loaded if found; if their ``_found`` value is non
        ``None`` (e.g. ``True`` or ``False``) they will be skipped. Typically
        this means this method is idempotent and becomes a no-op after the
        first run.

        Execution of this method does not imply merging; use `.merge` for that.
        """
        self._load_file(prefix='system')
        self._load_file(prefix='user')
        self._load_file(prefix='project')
        self._load_file(prefix='runtime', absolute=True)

    def _load_file(self, prefix, absolute=False):
        # Setup
        found = "{0}_found".format(prefix)
        path = "{0}_path".format(prefix)
        data = prefix
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
            path_prefix = getattr(self, "{0}_prefix".format(prefix))
            # Short circuit if loading seems unnecessary (eg for project config
            # files when not running out of a project)
            if path_prefix is None:
                return
            paths = [
                '.'.join((path_prefix, x))
                for x in self.file_suffixes
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
                    msg = "Config files of type {0!r} (from file {1!r}) are not supported! Please use one of: {2!r}"
                    raise UnknownFileType(msg.format(
                        type_, filepath, self.file_suffixes))
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

    def merge(self):
        """
        Merge all config sources, in order, to `.config`.

        Does not imply loading of config files or environment variables; use
        `.load_files` and/or `.load_shell_env` beforehand instead.
        """
        debug("Merging config sources in order...")
        debug("Defaults: {0!r}".format(self.defaults))
        merge_dicts(self.config, self.defaults)
        debug("Collection-driven: {0!r}".format(self.collection))
        merge_dicts(self.config, self.collection)
        self._merge_file('system', "System-wide")
        self._merge_file('user', "Per-user")
        self._merge_file('project', "Per-project")
        debug("Environment variable config: {0!r}".format(self.env))
        merge_dicts(self.config, self.env)
        self._merge_file('runtime', "Runtime")
        debug("Overrides: {0!r}".format(self.overrides))
        merge_dicts(self.config, self.overrides)

    def _merge_file(self, name, desc):
        # Setup
        desc += " config file" # yup
        found = getattr(self, "{0}_found".format(name))
        path = getattr(self, "{0}_path".format(name))
        data = getattr(self, name)
        # None -> no loading occurred yet
        if found is None:
            debug("{0} has not been loaded yet, skipping".format(desc))
        # True -> hooray
        elif found:
            debug("{0} ({1}): {2!r}".format(desc, path, data))
            merge_dicts(self.config, data)
        # False -> did try, did not succeed
        else:
            # TODO: how to preserve what was tried for each case but only for
            # the negative? Just a branch here based on 'name'?
            debug("{0} not found, skipping".format(desc))

    @property
    def paths(self):
        """
        An iterable of all successfully loaded config file paths.

        No specific order.
        """
        paths = []
        for prefix in "system user project runtime".split():
            value = getattr(self, "{0}_path".format(prefix))
            if value is not None:
                paths.append(value)
        return paths

    def _load_yaml(self, path):
        with open(path) as fd:
            return yaml.load(fd)

    def _load_json(self, path):
        with open(path) as fd:
            return json.load(fd)

    def _load_py(self, path):
        data = {}
        for key, value in six.iteritems(vars(imp.load_source('mod', path))):
            if key.startswith('__'):
                continue
            data[key] = value
        return data


def merge_dicts(base, updates):
    """
    Recursively merge dict ``updates`` into dict ``base`` (mutating ``base``.)

    * Values which are themselves dicts will be recursed into.
    * Values which are a dict in one input and *not* a dict in the other input
      (e.g. if our inputs were ``{'foo': 5}`` and ``{'foo': {'bar': 5}}``) are
      irreconciliable and will generate an exception.
    """
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
                    base[key] = value
        # New values just get set straight
        else:
            base[key] = value

def _merge_error(orig, new_):
    return AmbiguousMergeError("Can't cleanly merge {0} with {1}".format(
        _format_mismatch(orig), _format_mismatch(new_)
    ))

def _format_mismatch(x):
    return "{0} ({1!r})".format(type(x), x)
