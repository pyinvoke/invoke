from collections import deque, namedtuple

from .formatters import uppercased
from .exceptions import AmbiguousMergeError
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
            _merge(base=self, updates=formatted_adapter_data)

        # Subconfigs loading
        for subconfig in self._subconfigs.values():
            # If sub configs haven't set their own formatter,
            # ensure to cascade Config formatter to sub config objects
            if subconfig.formatter is None and self.formatter is not None:
                subconfig.formatter = self.formatter

            subconfig.load()


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
