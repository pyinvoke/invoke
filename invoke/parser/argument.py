class Argument(object):
    def __init__(self, name=None, names=(), kind=str, default=None,
        positional=False):
        if name and names:
            msg = "Cannot give both 'name' and 'names' arguments! Pick one."
            raise TypeError(msg)
        if not (name or names):
            raise TypeError("An Argument must have at least one name.")
        self.names = tuple(names if names else (name,))
        self.kind = kind
        self.raw_value = self._value = None
        self.default = default
        self.positional = positional

    def __str__(self):
        return "<%s: %s%s%s>" % (
            self.__class__.__name__,
            self.name,
            " (%s)" % (", ".join(self.nicknames)) if self.nicknames else "",
            "*" if self.positional else ""
        )

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.names[0]

    @property
    def nicknames(self):
        return self.names[1:]

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
