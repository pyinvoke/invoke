import types

from .base import Adapter


class Module(Adapter):
    def __init__(self, mod, *args, **kwargs):
        super(Module, self).__init__(*args, **kwargs)
        if not isinstance(mod, types.ModuleType):
            raise TypeError("mod should be instance of module")

        self.module = mod

    def load(self, formatter=None):
        self.data = dict((self.format(k, formatter), v) for k,v in vars(self.module).items()
                     if k.isupper())
