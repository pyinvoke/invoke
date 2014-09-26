from collections import defaultdict

try:
    from functools import reduce
except ImportError:
    pass

from ..utils import is_nested_key
from ..formatters import uppercased


Tree = lambda: defaultdict(Tree)


class Adapter(object):
    def __init__(self, formatter=None, strict=False, *keys, **mapping):
        self.data = Tree()
        self.formatter = formatter or uppercased
        self.strict = strict

        if self.strict is True:
            self.strictness_check()

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return '<{0} {1}>'.format(self.__str__(), id(self))

    def __getitem__(self, key):
        if is_nested_key(key):
            subkeys = key.split('.')
            return reduce(lambda d, k: d[k], subkeys, self.data)

        return self.data[key]

    def __setitem__(self, key, value):
        if is_nested_key(key):
            subkeys = key.split('.')

            reduce(lambda d, k: d[k], subkeys[:-1], self.data)[subkeys[-1]] = value
            return

        self.data[key] = value

    def strictness_check(self):
        pass

    def format(self, key, formatter=None):
        formatter = formatter or self.formatter
        return formatter(key)

    def load(self):
        raise NotImplementedError
