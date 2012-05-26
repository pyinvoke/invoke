class Argument(object):
    def __init__(self, name=None, names=(), value=None):
        if name and names:
            msg = "Cannot give both 'name' and 'names' arguments! Pick one."
            raise TypeError(msg)
        if not (name or names):
            raise TypeError("An Argument must have at least one name.")
        self.names = names if names else (name,)
        self.value_factory = value

    def __str__(self):
        valfact = (" %r" % (self.value_factory)) if self.value_factory else ""
        return "Arg: %r%s" % (self.names, valfact)

    @property
    def needs_value(self):
        return self.value_factory is not None
