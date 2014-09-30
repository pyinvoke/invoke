from os.path import abspath
from types import DictType

from .vendor.etcaetera.config import Config as EtcConfig
from .vendor.etcaetera.adapter import File, Defaults


def noop(s):
    """
    No-op 'formatter' for etcaetera adapters.

    For when we do not want auto upper/lower casing (currently, always).
    """
    return s


class DualAccess(object):
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
        obj._config = data
        return obj

    def __getattr__(self, key):
        try:
            return self._get(key)
        except KeyError:
            # Proxy most special vars to _config for dict procotol.
            if key in self._proxies:
                return getattr(self._config, key)
            # Otherwise, raise useful AttributeError to follow getattr proto.
            err = "No attribute or config key found for {0!r}".format(key)
            attrs = [x for x in dir(self.__class__) if not x.startswith('_')]
            err += "\n\nValid real attributes: {0!r}".format(attrs)
            err += "\n\nValid keys: {0!r}".format(self._config.keys())
            raise AttributeError(err)

    def __hasattr__(self, key):
        return key in self._config or key in self._proxies

    def __iter__(self):
        # For some reason Python is ignoring our __hasattr__ when determining
        # whether we support __iter__. BOO
        return iter(self._config)

    def __eq__(self, other):
        # Can't proxy __eq__ because the RHS will always be an obj of the
        # current class, not the proxied-to class, and that causes
        # NotImplemented.
        return self._config == other._config

    def __len__(self):
        # Can't proxy __len__ either apparently? ugh
        return len(self._config)

    def __setitem__(self, key, value):
        # ... or __setitem__? thanks for nothing Python >:(
        self._config[key] = value

    def __delitem__(self, key):
        # OK this is really getting annoying
        del self._config[key]

    def __getitem__(self, key):
        return self._get(key)

    def _get(self, key):
        value = self._config[key]
        if isinstance(value, DictType):
            value = DualAccess.from_data(value)
        return value

    # TODO: copy()?


class Config(DualAccess):
    """
    Invoke's primary configuration handling class.

    See :doc:`/concepts/configuration` for details on the configuration system
    this class implements, including the :ref:`configuration hierarchy
    <config-hierarchy>`.

    This class lightly wraps ``etcaetera.config.Config``, allowing for another
    level of configurability (re: which files are loaded and in what order) as
    well as convenient access to configuration values, which may be accessed
    using dict syntax::

        config['foo']

    or attribute syntax::

        config.foo

    .. warning::
        Any "real" attributes (methods, etc) on `Config` take precedence over
        settings values - so if you e.g. have a top level setting named
        ``load``, you *must* use dict syntax to access it.

    Nesting works the same way - dict config values are turned into objects
    which honor both the dictionary protocol and the attribute-access method::

       config['foo']['bar']
       config.foo.bar

    This class implements the entire dictionary protocol.
    """

    def __init__(self, **kwargs):
        """
        Creates a new config object, but does not load any configuration data.

        .. note::
            To load configuration data, call `~.Config.load` after
            initialization.

        For convenience, keyword arguments not listed below will be interpreted
        as top-level configuration keys, so one may say e.g.::
        
            c = Config(my_setting='my_value')
            c.load()
            print(c['my_setting']) # => 'my_value'

        :param str global_prefix:
            Path & partial filename for the global config file location. Should
            include everything but the dot & file extension.
            
            Default: ``/etc/invoke`` (e.g. ``/etc/invoke.yaml`` or
            ``/etc/invoke.json``).

        :param str user_prefix:
            Like ``global_prefix`` but for the per-user config file.

            Default: ``~/.invoke`` (e.g. ``~/.invoke.yaml``).

        :param iterable adapters:
            An iterable of `Adapters` to use instead of the default
            :ref:`hierarchy <config-hierarchy>`.

            If this option is given, ``global_prefix`` and ``user_prefix`` will
            be ignored.

        .. _Adapters: http://etcaetera.readthedocs.org/en/0.4.0/howto.html#adapters
        """
        adapters = kwargs.pop('adapters', None)
        global_prefix = kwargs.pop('global_prefix', '/etc/invoke')
        user_prefix = kwargs.pop('user_prefix', '~/.invoke')
        c = EtcConfig(formatter=noop)
        # Explicit adapter set
        if adapters is not None:
            c.register(*adapters)
        # The Hierarchy
        else:
            c.register(File("{0}.yaml".format(global_prefix)))
            c.register(File("{0}.yaml".format(user_prefix)))
        # Init-time defaults
        self._config = c
        self.set_defaults(kwargs)

    def set_defaults(self, data):
        """
        Assign ``data`` as the default configuration.

        .. warning::
            If values were also given during `~.Config.__init__`, they will
            be **overridden** by the ``data`` given to this method - no merging
            will occur.

        .. warning::
            Use of `.Config.load` is required to update the internal
            configuration data, even if you've called it previously this
            session. Failure to do so will result in stale data.

        :param dict data:
            Dictionary to use as the default data set for this configuration.
        """
        # Must reinforce 'noop' here as Defaults calls load() in init()
        self._config.register(Defaults(data, formatter=noop))

    def load(self):
        """
        Performs loading and merging of all config sources.

        See :ref:`config-hierarchy` for details on load order and file
        locations.
        """
        return self._config.load()
