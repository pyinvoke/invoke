class Argument(object):
    """
    A command-line argument/flag.

    :param name:
        Syntactic sugar for ``names=[<name>]``. Giving both ``name`` and
        ``names`` is invalid.
    :param names:
        List of valid identifiers for this argument. For example, a "help"
        argument may be defined with a name list of ``['-h', '--help']``.
    :param kind:
        Type factory & parser hint. E.g. ``int`` will turn the default text
        value parsed, into a Python integer; and ``bool`` will tell the
        parser not to expect an actual value but to treat the argument as a
        toggle/flag.
    :param default:
        Default value made available to the parser if no value is given on the
        command line.
    :param help:
        Help text, intended for use with ``--help``.
    :param positional:
        Whether or not this argument's value may be given positionally. When
        ``False`` (default) arguments must be explicitly named.
    :param optional:
        Whether or not this (non-``bool``) argument requires a value.
    """
    def __init__(self, name=None, names=(), kind=str, default=None, help=None,
        positional=False, optional=False, attr_name=None):
        if name and names:
            msg = "Cannot give both 'name' and 'names' arguments! Pick one."
            raise TypeError(msg)
        if not (name or names):
            raise TypeError("An Argument must have at least one name.")
        self.names = tuple(names if names else (name,))
        self.kind = kind
        self.raw_value = self._value = None
        self.default = default
        self.help = help
        self.positional = positional
        self.optional = optional
        self.attr_name = attr_name

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
        return self.attr_name or self.names[0]

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
        self.set_value(arg, cast=True)

    def set_value(self, value, cast=True):
        """
        Actual explicit value-setting API call.

        Sets ``self.raw_value`` to ``value`` directly.

        Sets ``self.value`` to ``self.kind(value)``, unless ``cast=False`` in
        which case the raw value is also used.
        """
        self.raw_value = value
        self._value = (self.kind if cast else lambda x: x)(value)
