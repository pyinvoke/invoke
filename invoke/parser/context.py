from ..vendor.lexicon import Lexicon

from .argument import Argument


def to_flag(name):
    if len(name) == 1:
        return '-' + name
    return '--' + name


class Context(object):
    """
    Parsing context with knowledge of flags & their format.

    Generally associated with the core program or a task.

    When run through a parser, will also hold runtime values filled in by the
    parser.
    """
    def __init__(self, name=None, aliases=(), args=()):
        """
        Create a new ``Context`` named ``name``, with ``aliases``.

        ``name`` is optional, and should be a string if given. It's used to
        tell Context objects apart, and for use in a Parser when determining
        what chunk of input might belong to a given Context.

        ``aliases`` is also optional and should be an iterable containing
        strings. Parsing will honor any aliases when trying to "find" a given
        context in its input.

        May give one or more ``args``, which is a quick alternative to calling
        ``for arg in args: self.add_arg(arg)`` after initialization.
        """
        self.args = Lexicon()
        self.positional_args = []
        self.flags = Lexicon()
        self.name = name
        self.aliases = aliases
        for arg in args:
            self.add_arg(arg)

    def __str__(self):
        aliases = (" (%s)" % ', '.join(self.aliases)) if self.aliases else ""
        name = (" %r%s" % (self.name, aliases)) if self.name else ""
        args = (": %r" % (self.args,)) if self.args else ""
        return "<Context%s%s>" % (name, args)

    def __repr__(self):
        return str(self)

    def add_arg(self, *args, **kwargs):
        """
        Adds given ``Argument`` (or constructor args for one) to this context.

        The Argument in question is added to two dict attributes:

        * ``args``: "normal" access, i.e. the given names are directly exposed
          as keys.
        * ``flags``: "flaglike" access, i.e. the given names are translated
          into CLI flags, e.g. ``"foo"`` is accessible via ``flags['--foo']``.
        """
        # Normalize
        if len(args) == 1 and isinstance(args[0], Argument):
            arg = args[0]
        else:
            arg = Argument(*args, **kwargs)
        # Test
        for name in arg.names:
            if name in self.args:
                msg = "Tried to add an argument named %r but one already exists!"
                raise ValueError(msg % name)
        # All arguments added to .args
        main = arg.name
        self.args[main] = arg
        # Positional and nonpositional args get split up between
        # .positional_args and .flags
        if arg.positional:
            self.positional_args.append(arg)
        self.flags[to_flag(main)] = arg
        # All args get their aliases added to .args too
        for name in arg.nicknames:
            self.args.alias(name, to=main)
            # But only alias flags within .flags
            if not arg.positional:
                self.flags.alias(to_flag(name), to=to_flag(main))

    @property
    def needs_positional_arg(self):
        return any(x.value is None for x in self.positional_args)
