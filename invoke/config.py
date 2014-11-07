import copy
import imp
import json
import os
from os.path import join
from types import DictType, BooleanType, StringTypes, ListType, TupleType

from .vendor import six
if six.PY3:
    from .vendor import yaml3 as yaml
else:
    from .vendor import yaml2 as yaml

from .exceptions import AmbiguousEnvVar, UncastableEnvVar
from .util import debug


#: Sentinel object denoting that a config file was sought and not found.
#: Differentiated from ``None`` which indicates that no file loading has
#: occurred yet.
NOT_FOUND = object()


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
        Load values from the shell environment.

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
        Update collection-driven config data.

        `.set_collection` is intended for use by the core task execution
        machinery, which is responsible for obtaining per-task
        collection-driven data. See :ref:`collection-configuration` for
        details.
        """
        self.collection = data

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

    def load_files(self):
        """
        Load any unloaded/un-searched-for config file sources.

        Specifically, any file sources whose ``_path`` values are ``None`` will
        be sought and loaded if found. Path values which are set to a string or
        `NOT_FOUND` will be skipped. Typically this means this method is
        idempotent and becomes a no-op after the first run.

        Execution of this method does not imply merging; use `merge` for that.
        """
        # TODO: make subroutine parameterized on stored path, prefix, and
        # optional suffixes.
        # system: use system_prefix + file_suffixes
        if self.system_path is None:
            for suffix in self.file_suffixes:
                path = '.'.join((self.system_prefix, suffix))
                try:
                    self.system = _loaders[suffix](path)
                    self.system_path = path
                    debug("Loaded systemwide config file {0}".format(path))
                    break
                # Typically means 'no such file', so just note & skip past.
                except IOError as e:
                    err = "Received exception ({0!r}) loading {1}, skipping."
                    debug(err.format(e.strerror, path))
            # Still None -> no suffixed paths were found, record this fact
            if self.system_path is None:
                self.system_path = NOT_FOUND
        # user: ditto
        # project: use project_home + 'invoke' + file_suffixes
        # runtime: use runtime_path


    def merge(self):
        """
        Merge all config sources, in order, to `config`.

        Does not imply loading of config files or environment variables; use
        `load_files` and/or `load_shell_env` beforehand instead.
        """
        self.config = {}
        debug("Merging config sources in order...")
        debug("Defaults: {0!r}".format(self.defaults))
        _merge(self.config, self.defaults)
        debug("Collection-driven: {0!r}".format(self.collection))
        _merge(self.config, self.collection)
        self._merge_file('system', "System-wide")
        self._merge_file('user', "Per-user")
        self._merge_file('project', "Per-project")
        # TODO: determine if env has been loaded yet?
        debug("Environment variable config: {0!r}".format(self.env))
        self._merge_file('runtime', "Runtime")
        debug("Overrides: {0!r}".format(self.overrides))
        _merge(self.config, self.overrides)

    def _merge_file(self, name, desc):
        desc += " config file" # yup
        path = getattr(self, "{0}_path".format(name))
        data = getattr(self, name)
        if path is None:
            debug("{0} has not been loaded yet, skipping".format(desc))
        elif path is NOT_FOUND:
            # Details about exact paths searched is debug'd earlier
            debug("{0} not found, skipping".format(desc))
        else:
            debug("{0} ({1}): {2!r}".format(desc, path, data))
            _merge(self.config, data)

    def __getattr__(self, key):
        print "Config.__getattr__({0!r})".format(key)
        self.load_files()
        self.merge()
        return super(Config, self).__getattr__(key)


def _merge(base, updates):
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
                    _merge(base[key], value)
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


#
# File loading
#

def _load_yaml(path):
    with open(path) as fd:
        return yaml.load(fd)

def _load_json(path):
    with open(path) as fd:
        return json.load(fd)

def _load_python(path):
    data = {}
    for key, value in vars(imp.load_source('mod', path)).iteritems():
        if key.startswith('__'):
            continue
        data[key] = value
    return data

_loaders = {
    'yaml': _load_yaml,
    'json': _load_json,
    'py': _load_python,
}
