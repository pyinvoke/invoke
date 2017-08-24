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
    :param attr_name:
        A Python identifier/attribute friendly name, typically filled in with
        the underscored version when ``name``/``names`` contain dashes.
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

    def __repr__(self):
        nicks = ""
        if self.nicknames:
            nicks = " ({0})".format(", ".join(self.nicknames))
        flags = ""
        if self.positional or self.optional:
            flags = " "
        if self.positional:
            flags += "*"
        if self.optional:
            flags += "?"
        # TODO: store this default value somewhere other than signature of
        # Argument.__init__?
        kind = ""
        if self.kind != str:
            kind = " [{0}]".format(self.kind.__name__)
        return "<{0}: {1}{2}{3}{4}>".format(
            self.__class__.__name__,
            self.name,
            nicks,
            kind,
            flags,
        )

    @property
    def name(self):
        """
        The canonical attribute-friendly name for this argument.

        Will be ``attr_name`` (if given to constructor) or the first name in
        ``names`` otherwise.
        """
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

        For repeated value setting, just convert ``self.raw_value`` to a list.
        So does ``self.value``.
        """
        casted_value = (self.kind if cast else lambda x: x)(value)
        if self.raw_value is None:
            self.raw_value = value
            self._value = casted_value
        elif isinstance(self.raw_value, list):
            self.raw_value.append(value)
            self._value.append(casted_value)
        else:
            self.raw_value = [self.raw_value, value]
            self._value = [self._value, casted_value]
