import copy
import os
from os.path import join
from types import DictType, BooleanType, StringTypes, ListType, TupleType

from .exceptions import AmbiguousEnvVar, UncastableEnvVar
from .util import debug


class NestedEnv(object):
    """
    Custom etcaetera adapter for handling env vars (more flexibly than Env).
    """
    def __init__(self, config, prefix=None):
        """
        Initialize this adapter with a handle to a live Config object.

        :param config:
            An already-loaded Config object which can be introspected for its
            keys.

        :param str prefix:
            A prefix string used when seeking env vars; see `.Config`.
        """
        super(NestedEnv, self).__init__()
        self._config = config
        self._prefix = prefix
        self.data = {}

    def load(self, formatter=None):
        # NOTE: This accepts a formatter argument because that's the API.
        # However we don't use it (or the centrally defined one) because we
        # have specific requirements for how keys are treated in this adapter.
        # Meh!

        # Obtain allowed env var -> existing value map
        env_vars = self._crawl(key_path=[], env_vars={})
        debug("Scanning for env vars according to prefix: {1!r}, mapping: {0!r}".format(env_vars, self._prefix))
        # Check for actual env var (honoring prefix) and try to set
        for env_var, key_path in env_vars.iteritems():
            real_var = (self._prefix or "") + env_var
            if real_var in os.environ:
                self._path_set(key_path, os.environ[real_var])

    def _crawl(self, key_path, env_vars):
        """
        Examine config at location ``key_path`` & return potential env vars.

        Uses ``env_vars`` dict to determine if a conflict exists, and raises an
        exception if so. This dict is of the following form::

            {
                'EXPECTED_ENV_VAR_HERE': ['actual', 'nested', 'key_path'],
                ...
            }

        Returns another dictionary of new keypairs as per above.
        """
        new_vars = {}
        obj = self._path_get(key_path)
        # Sub-dict -> recurse
        if hasattr(obj, 'keys') and hasattr(obj, '__getitem__'):
            for key in obj.keys():
                merged_vars = dict(env_vars, **new_vars)
                merged_path = key_path + [key]
                crawled = self._crawl(merged_path, merged_vars)
                # Handle conflicts
                for key in crawled:
                    if key in new_vars:
                        err = "Found >1 source for {0}"
                        raise AmbiguousEnvVar(err.format(key))
                # Merge and continue
                new_vars.update(crawled)
        # Other -> is leaf, no recursion
        else:
            new_vars[self._to_env_var(key_path)] = key_path
        return new_vars

    def _to_env_var(self, key_path):
        return '_'.join(key_path).upper()

    def _path_get(self, key_path):
        # Gets are from self._config because that's what determines valid env
        # vars and/or values for typecasting.
        obj = self._config
        for key in key_path:
            obj = obj[key]
        return obj

    def _path_set(self, key_path, value):
        # Sets are to self.data since that's what we are presenting to the
        # outer config object and debugging.
        obj = self.data
        for key in key_path[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]
        old = self._path_get(key_path)
        new_ = self._cast(old, value)
        obj[key_path[-1]] = new_

    def _cast(self, old, new_):
        if isinstance(old, BooleanType):
            return new_ not in ('0', '')
        elif isinstance(old, StringTypes):
            return new_
        elif old is None:
            return new_
        elif isinstance(old, (ListType, TupleType)):
            err = "Can't adapt an environment string into a {0}!"
            err = err.format(type(old))
            raise UncastableEnvVar(err)
        else:
            return old.__class__(new_)


class ExclusiveFile(object):
    """
    File-loading config adapter that looks for one of N possible suffixes.

    For example, ``ExclusiveFile(prefix='/etc/invoke', suffixes=['yaml',
    'json'])`` behaves similar to loading both of
    ``File('/etc/invoke.yaml')`` + ``File('/etc/invoke.json')``, with the
    distinction that if ``/etc/invoke.yaml`` is succesfully loaded, the JSON
    file is **not** loaded at all. (This means that the order of the
    ``suffixes`` parameter matters.)

    This provides an unambiguous config source-loading process, simplifying
    troubleshooting and (hopefully) reduces potential for confusion.

    :param str prefix:
        Everything but the file extension, e.g. ``/etc/invoke`` to load up
        files like ``/etc/invoke.yaml``.

    :param iterable suffixes:
        Optional iterable of file extensions like ``"yaml"`` or ``"json"``. Do
        not include any leading periods (i.e. don't say
        ``ExclusiveFile('/etc/invoke', '.yaml')``).

        Defaults to ``('yaml', 'json', 'py')``.
    """
    def __init__(self, prefix, suffixes=None):
        if suffixes is None:
            suffixes = ('yaml', 'json', 'py')
        self.prefix = prefix
        self.suffixes = suffixes
        self.adapters = [
            File(
                "{0}.{1}".format(prefix, x),
                python_uppercase=False,
                strict=False
            )
            for x in suffixes
        ]
        self.data = {}
        self.loaded = None

    def __str__(self):
        return "ExclusiveFile({0}.{{{1}}})".format(self.prefix, ','.join(self.suffixes))

    def load(self, formatter=None):
        for adapter in self.adapters:
            adapter.load(formatter=formatter)
            # Simply offload data from the 1st one to be found.
            # If none are found, our data remains empty as initialized.
            if adapter.found:
                self.data = adapter.data
                self.loaded = adapter.filepath
                return


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
            err += "\n\nValid real attributes: {0!r}".format(attrs)
            err += "\n\nValid keys: {0!r}".format(self.config.keys())
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
        if isinstance(value, DictType):
            value = DataProxy.from_data(value)
        return value

    def __str__(self):
        return str(self.config)

    def __unicode__(self):
        return unicode(self.config)

    def __repr__(self):
        return repr(self.config)

    # TODO: copy()?


class Config(DataProxy):
    """
    Invoke's primary configuration handling class.

    See :doc:`/concepts/configuration` for details on the configuration system
    this class implements, including the :ref:`configuration hierarchy
    <config-hierarchy>`. The rest of this class' documentation assumes
    familiarity with that document.

    Lifecycle
    ---------

    Configuration data is constructed piecemeal starting at initialization time
    and config sources are loaded lazily upon request. For example, pure-Python
    configuration does not load from the filesystem or shell environment::

        c = Config(defaults={'foo': 'bar'})
        c.foo # No action taken, defaults are the only thing consulted

    If filesystem paths prefixes are given, they are scanned at access time and
    merged into the final config::

        c = Config(system_prefix='/etc/invoke')
        c.foo # Attempts to load files like /etc/invoke.yaml
        c.foo # No filesystem action taken this time

    The merged config is regenerated any time config sources are updated, such
    as when Invoke's core machinery tells the default config object that it's
    time to load data from the shell environment::

        c = Config(system_prefix='/etc/invoke')
        c.foo # Merging (and file load) occurs
        c.foo # No merging nor file loading - cache only
        c.load_shell_env() # Merging (but no file loads - only env)
        c.foo # Again, no merging or file loading takes place

    Access
    ------

    Configuration values may be accessed using dict syntax::

        config['foo']

    or attribute syntax::

        config.foo

    .. warning::
        Any "real" attributes (methods, etc) on `Config` take precedence over
        settings values - so if you have top level settings named ``clone``,
        ``defaults``, etc, you *must* use dict syntax to access it.

    Nesting works the same way - dict config values are turned into objects
    which honor both the dictionary protocol and the attribute-access method::

       config['foo']['bar']
       config.foo.bar

    Non-data attributes & methods
    -----------------------------

    This class implements the entire dictionary protocol: methods such as
    ``keys``, ``values``, ``items``, ``pop`` and so forth should all function
    as they do on regular dicts.

    Individual configuration 'levels' and their source locations (if
    applicable) may be accessed via attributes such as
    `.project`/`.project_file` and so forth - see the
    documentation for individual members below for details.
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
        # Technically an implementation detail - do not expose in public API.
        # Stores merged configs and is accessed via DataProxy.
        self.config = None

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
        #: Data loaded from the system config file.
        self.system = {}

        #: Path prefix searched for per-user config files.
        self.user_prefix = '~/.invoke' if user_prefix is None else user_prefix
        #: Path to loaded user config file, if any.
        self.user_path = None
        #: Data loaded from the per-user config file.
        self.user = {}

        #: Parent directory of the current root tasks file, if applicable.
        self.project_home = project_home
        #: Path to loaded per-project config file, if any.
        self.project_path = None
        #: Data loaded from the per-project config file.
        self.project = {}

        #: Environment variable name prefix
        # TODO: make this INVOKE_ and update tests, just deal
        self.env_prefix = '' if env_prefix is None else env_prefix
        #: Config data loaded from the shell environment.
        self.env = {}

        #: Path to the user-specified runtime config file.
        self.runtime_path = runtime_path
        # Data loaded from the runtime config file.
        self.runtime = {}

        #: Overrides - highest possible config level. Typically filled in from
        #: command-line flags.
        self.overrides = {} if overrides is None else overrides

    def load_shell_env(self):
        """
        Load values from the shell environment, then trigger a config merge.

        This method is idempotent and does nothing if ``.shell`` is already
        non-``None``.

        `.load_shell_env` is intended for execution late in a `.Config`
        object's lifecycle, once all other sources have been merged. Loading
        from the shell is not terrifically expensive, but must be done at a
        specific point in time to ensure the "only valid options" behavior
        works correctly.
        
        See :ref:`env-vars` for details on this design decision and other info
        re: how environment variables are scanned and loaded.
        """
        pass

    def set_collection(self, data):
        """
        Update collection-driven config data, then trigger a config merge.

        This method is idempotent and does nothing if ``.collection`` is
        already non-``None``.

        `.set_collection` is intended for use by the core task execution
        machinery, which is responsible for obtaining per-task
        collection-driven data. See :ref:`collection-configuration` for
        details.
        """
        pass

    def load(self, collection=None):
        """
        Performs loading and merging of all config sources.

        See :ref:`config-hierarchy` for details on load order and file
        locations.

        :param dict collection:
            A dict containing collection-driven config data. Default: ``{}``.
        """
        # Pull in defaults (we do so at this level because typically we won't
        # know about collection-level default values until closer to runtime.
        if collection is None:
            collection = {}
        # NOTE: can't use etc.AdapterSet.appendleft here, it is buggy, no time
        # to fix right now. Just insert at position 1 after the Defaults we
        # already know is there.
        self.config.adapters.insert(1, Basic(collection))
        # Now that we have all other sources defined, we can load the Env
        # adapter. This sadly requires a 'pre-load' call to .load() so config
        # files get slurped up.
        self.config.load()
        env = NestedEnv(config=self.config, prefix=self.env_prefix)
        # Must break encapsulation a tiny bit here to ensure env vars come
        # before runtime config files in the hierarchy. It's the least bad way
        # right now given etc.Config's api.
        self.config.adapters.insert(len(self.config.adapters) - 2, env)
        # Re-load() so that our values get applied in the right slot in the
        # hierarchy.
        self.config.load()
        debug("Loading & merging config adapters in order...")
        for adapter in self.config.adapters:
            if isinstance(adapter, File) and not adapter.found:
                debug("Didn't see any {0}, skipping".format(adapter))
            elif isinstance(adapter, ExclusiveFile):
                if adapter.loaded is None:
                    debug("Didn't see any of {0}, skipping".format(
                        adapter))
                else:
                    debug("{0} loaded {1}, got {2!r}".format(
                        adapter, adapter.loaded, adapter.data))
            else:
                # Wrap adapter in dict() so defaultdicts print nicer
                debug("Loaded {0}, got {1!r}".format(
                    adapter, dict(adapter.data)))
        debug("Final merged config: {0!r}".format(self.config))

    def clone(self):
        """
        Return a copy of this configuration object.

        The new object will be identical in terms of configured sources and any
        loaded/merged data, but will be a distinct object with no shared
        mutable state.
        """
        # New config w/ formatter preserved
        c = EtcConfig(formatter=self.config.formatter)
        # New adapters, ditto + deepcopy internal data
        adapters = []
        for old in self.config.adapters:
            c.register(_clone_adapter(old))
        # Then deepcopy loaded data in case already loaded (we don't
        # necessarily know at this point if loading has occurred).
        c.update(copy.deepcopy(dict(self.config)))
        # All set
        new = Config(env_prefix=self.env_prefix)
        new.config = c
        return new


def _clone_adapter(old):
    if isinstance(old, (Defaults, Overrides)):
        new = old.__class__(formatter=old.formatter)
    elif isinstance(old, File):
        new = File(
            filepath=old.filepath,
            python_uppercase=old.python_uppercase,
            formatter=old.formatter,
        )
    elif isinstance(old, ExclusiveFile):
        new = ExclusiveFile(
            prefix=old.prefix,
            suffixes=old.suffixes,
        )
    elif isinstance(old, NestedEnv):
        new = NestedEnv(old._config)
    elif isinstance(old, Dummy):
        new = Dummy()
    elif isinstance(old, Basic):
        new = Basic(old.data)
    else:
        raise TypeError("No idea how to clone {0}!".format(old.__class__))
    new.data = copy.deepcopy(old.data)
    return new
