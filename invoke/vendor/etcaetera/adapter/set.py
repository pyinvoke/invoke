from collections import deque

from .base import Adapter
from .defaults import Defaults
from .overrides import Overrides


class AdapterSet(deque):
    def __init__(self, *adapters):
        super(AdapterSet, self).__init__()
        self._load_adapters(adapters)

    def __repr__(self):
        return 'AdapterSet{0}'.format(self.__str__())

    def __str__(self):
        return '({0})'.format(', '.join([a.__str__() for a in self]))

    def __setitem__(self, key, value):
        if isinstance(value, Defaults) and key != 0:
                raise IndexError("Defaults adapter shall always be unique and first")  
        elif isinstance(value, Overrides) and key != (len(self) - 1):
                raise IndexError("Overrides adapter shall always be unique and last")

        super(AdapterSet, self).__setitem__(key, value)

    @property
    def defaults(self):
        if not hasattr(self, '_defaults'):
            self._defaults = None
        return self._defaults

    @defaults.setter
    def defaults(self, value):
        if not isinstance(value, (dict, Defaults)):
            raise TypeError("Attribute must be of Defaults or dict type")

        # If a dictionary was provided convert it to a Defaults obj
        if isinstance(value, dict):
            value = Defaults(data=value)

        if len(self) == 0:
            self.appendleft(value)
        else:
            # If first member is already a Defaults adapter,
            # replace it
            if isinstance(self[0], Defaults):
                self[0] = value
            # Otherwise append the Defaults on left of the AdapterSet
            else:
                self.appendleft(value)

        self._defaults = value

    @property
    def overrides(self):
        if not hasattr(self, '_overrides'):
            self._overrides = None
        return self._overrides

    @overrides.setter
    def overrides(self, value):
        if not isinstance(value, (dict, Overrides)):
            raise TypeError("Attribute must be of Overrides or dict type")

        # If a dictionary was provided convert it to a Overrides obj
        if isinstance(value, dict):
            value = Overrides(data=value)

        if len(self) == 0:
            self.append(value)
        else:
            # If last member is already an Overrides adapter,
            # replace it
            if isinstance(self[len(self) - 1], Overrides):
                self[len(self) - 1] = value
            # Otherwise add the adapter on the right of the AdapterSet
            else:
                self.append(value)

        self._overrides = value

    def appendleft(self, adapter):
        if not isinstance(adapter, Adapter):
            raise TypeError

        if isinstance(adapter, Defaults):
            if len(self) >= 1 and isinstance(self[0], Defaults):
                raise ValueError("Cannot add two defaults adapter to the same set")
            else:
                # If provided adatper is a Defaults and there are no one present
                # in the set yet, appendleft it, and set _defaults to it
                super(AdapterSet, self).appendleft(adapter)
                self._defaults = adapter
        elif isinstance(adapter, Overrides):
            if len(self) >= 1 and isinstance(self[0], Overrides):
                raise ValueError("Cannot add two overrides adapter to the same set")
            else:
                # If provided adatper is an Overrides and there are no one present
                # in the set yet, appendleft it, and set _overrides to it
                super(AdapterSet, self).appendleft(adapter)
                self._overrides = adapter
        else:
            super(AdapterSet, self).appendleft(adapter)

    def append(self, adapter):
        if not isinstance(adapter, Adapter):
            raise TypeError

        if isinstance(adapter, Overrides):
            if len(self) >= 1 and isinstance(self[-1], Overrides):
                raise ValueError("Cannot add two overrides adapter to the same set")
            else:
               # If provided adatper is an Overrides and there are no one present
                # in the set yet, append it, and set _overrides to it
                super(AdapterSet, self).append(adapter)
                self._overrides = adapter
        elif isinstance(adapter, Defaults):
            if len(self) >= 1 and isinstance(self[0], Defaults):
                raise ValueError("Cannot add two overrides adapter to the same set")
            else:
                # If provided adatper is a Defaults and there are no one present
                # in the set yet, append it, and set _defaults to it
                super(AdapterSet, self).append(adapter)
                self._defaults = adapter
        else:
            super(AdapterSet, self).append(adapter)

    def insert(self, index, adapter):
        if index < 0:
            raise IndexError("AdapterSet doesn't support negative indexing")
        
        if not isinstance(adapter, Adapter):
            raise TypeError("AdapterSet can only contain Adapter type objects") 

        if index == 0:
            self.appendleft(adapter)
        elif index >= len(self):
            self.append(adapter)
        else:
            # Use deque.rotate to roll forward (right) enough that we can
            # append the new one at desired spot, then use rotate with a
            # negative index to roll back to our starting point.
            focus = len(self) - index
            self.rotate(focus)
            self.append(adapter)
            self.rotate(-focus)

    def _load_adapters(self, adapters):
        for index, adapter in enumerate(adapters):
            if (isinstance(adapter, Defaults) and
                (self.defaults is not None or index != 0)):
                raise ValueError("Cannot add two defaults adapter to the same set")
            elif (isinstance(adapter, Overrides) and
                  (self.overrides is not None or index < (len(adapters) - 1))):
                raise ValueError("Cannot add two overrides adapters to the same set")
            elif not isinstance(adapter, Adapter):
                raise TypeError("AdapterSet can only contain Adapter type objects")

            self.append(adapter)
