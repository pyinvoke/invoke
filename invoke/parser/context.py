from lexicon import Lexicon

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
        self.flags = Lexicon()
        self.name = name
        self.aliases = aliases
        for arg in args:
            self.add_arg(arg)

    def __str__(self):
        aliases = (" (%s)" % ', '.join(self.aliases)) if self.aliases else ""
        name = (" %s%s" % (self.name, aliases)) if self.name else ""
        return "Context%s: %r" % (name, self.args)

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
        # Add
        main = arg.names[0]
        self.args[main] = arg
        self.flags[to_flag(main)] = arg
        for name in arg.names[1:]:
            self.args.alias(name, to=main)
            self.flags.alias(to_flag(name), to=to_flag(main))

    def help_for(self, flag):
        """
        Return help line string for given ``flag``.
        """
        # Obtain arg obj
        if flag not in self.flags:
            raise ValueError("%r is not a valid flag for this context" % flag)
        arg = self.flags[flag]
        # Show all potential names for this flag in the output
        names = list(set([flag] + self.flags.aliases_of(flag)))
        # Determine expected value type, if any
        value = {
            str: 'STRING',
        }.get(arg.kind)
        # Format & go
        full_names = []
        for name in names:
            sep = " " if len(name.strip('-')) == 1 else "="
            full_names.append(name + ((sep + value) if value else ""))
        namestr = ", ".join(sorted(full_names, key=len))
        helpstr = ((" " * 8) + arg.help) if arg.help else ""
        return namestr + helpstr

    def help_lines(self):
        """
        Return sorted iterable of help lines for all member Arguments.

        Sorts like so:

        * General sort is alphanumerically
        * Short flags win over long flags
        * But Arguments with *only* long flags and *no* short flags will come
          first.

        This will result in a help list like so:

            --alpha
            --beta
            -a, --aaaagh
            -b, --bah
            -c
        """
        return map(self.help_for, sorted(self.flags))
