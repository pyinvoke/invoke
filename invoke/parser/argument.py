class Argument(object):
    def __init__(self, name=None, names=(), kind=str, default=None):
        if name and names:
            msg = "Cannot give both 'name' and 'names' arguments! Pick one."
            raise TypeError(msg)
        if not (name or names):
            raise TypeError("An Argument must have at least one name.")
        self.names = names if names else (name,)
        self.kind = kind
        self.raw_value = self._value = None
        self.default = default

    def __str__(self):
        return "Arg: %r (%s)" % (self.names, self.kind)

    @property
    def takes_value(self):
        return self.kind is not bool

    @property
    def value(self):
        return self._value if self._value is not None else self.default

    @value.setter
    def value(self, arg):
        self.raw_value = arg
        self._value = self.kind(arg)
