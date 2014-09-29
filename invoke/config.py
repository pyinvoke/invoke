from .vendor.etcaetera.config import Config as EtcConfig
from .vendor.etcaetera.adapter import File


class Config(object):
    """
    Invoke's primary configuration handling class.

    See :doc:`/concepts/configuration` for details on the configuration system
    this class implements, including the :ref:`configuration hierarchy
    <config-hierarchy>`.

    Lightly wraps ``etcaetera.config.Config``, allowing for another level of
    configurability (re: which files are loaded and in what order) as well as
    convenient access to configuration values, which may be accessed using
    dict syntax::

        config['foo']

    or attribute syntax::

        config.foo

    .. warning::
        Any "real" attributes (methods, etc) on `Config` take precedence over
        settings values - so if you e.g. have a top level setting named
        ``load``, you *must* use dict syntax to access it.

    Nesting works the same way - dict config values are transparently turned
    into objects which honor both the dictionary protocol and the
    attribute-access method::

       config['foo']['bar']
       config.foo.bar
    """

    def __init__(self):
        """
        Creates a new config object, but does not load any configuration data.

        .. note::
            To load configuration data, call `~.Config.load` after
            initialization.

        For convenience, keyword arguments not listed below will be interpreted
        as top-level configuration keys, so one may say e.g.::
        
            c = Config(my_setting='my_value')
            print(c['my_setting']) # => 'my_value'

        :param str global_prefix:
            Path & partial filename for the global config file location. Should
            include everything but the dot & file extension.
            
            The final result (including extension) will be turned into a fully
            qualified file path and have system-appropriate expansion performed
            (tildes and so forth).
            
            Default: ``/etc/invoke`` (e.g. ``/etc/invoke.yaml`` or
            ``/etc/invoke.json``).

        :param str user_prefix:
            Like ``global_prefix`` but for the per-user config file.

            Default: ``~/.invoke`` (e.g. ``~/.invoke.yaml``).
        """
        pass

    def load(self):
        """
        Performs loading and merging of all config sources.

        See :ref:`config-hierarchy` for details on load order and file
        locations.
        """
        pass
