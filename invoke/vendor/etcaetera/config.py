from collections import deque, namedtuple

from .formatters import uppercased
from .adapter import (
    Adapter,
    AdapterSet,
    Defaults,
    Overrides,
    Env
)


class Config(dict):
    def __init__(self, defaults=None, overrides=None, formatter=None, *adapters):
        self.formatter = formatter or uppercased
        self._subconfigs = {}

        self.adapters = AdapterSet(*adapters)

        if defaults is not None:
            self.defaults = defaults

        if overrides is not None:
            self.overrides = overrides

    def register(self, *adapters):
        """Registers an adapter to be applied by config"""
        for adapter in adapters:
            if isinstance(adapter, Defaults):
                self.adapters.defaults = adapter
            elif isinstance(adapter, Overrides):
                self.adapters.overrides = adapter
            else:
                if self.adapters.overrides is not None:
                    # If adapters contains an Overrides adapter,
                    # insert at the index before it.
                    self.adapters.insert(len(self.adapters) - 1, adapter)
                else:
                    # Otherwise, append it
                    self.adapters.append(adapter)

    def add_subconfig(self, name, subconfig):
        """Attaches a sub-config to the current Config object"""
        if not isinstance(subconfig, Config):
            raise TypeError(
                "Subconfig has to be of Config type. "
                "Got {0} instead".format(type(subconfig))
            )

        self._subconfigs[name] = subconfig
        setattr(self, name, subconfig) 

    @property
    def defaults(self):
        return self.adapters.defaults

    @defaults.setter
    def defaults(self, value):
        self.adapters.defaults = value

    @property
    def overrides(self):
        return self.adapters.overrides

    @overrides.setter
    def overrides(self, value):
        self.adapters.overrides = value

    @property
    def adapters(self):
        if not hasattr(self, '_adapters'):
            self._adapters = AdapterSet()
        return self._adapters

    @adapters.setter
    def adapters(self, value):
        # Ensure adapters is a list of adapters
        if not isinstance(value, (list, AdapterSet)):
            raise TypeError("adapters value has to be a list or AdapterSet.")

        self._adapters = AdapterSet(*value)

    def load(self):
        # Adapters loading
        for adapter in self.adapters:
            adapter.load(formatter=self.formatter)
            formatted_adapter_data = dict((self.formatter(k), v) for k, v in adapter.data.items())
            self.update(formatted_adapter_data)

        # Subconfigs loading
        for subconfig in self._subconfigs.values():
            # If sub configs haven't set their own formatter,
            # ensure to cascade Config formatter to sub config objects
            if subconfig.formatter is None and self.formatter is not None:
                subconfig.formatter = self.formatter

            subconfig.load()

