import re


class Argument(object):
    def __init__(self, long_name=None, short_name=None, needs_value=False):
        self.long_name = long_name
        self.short_name = short_name
        self.needs_value = needs_value

    def answers_to(self, arg):
        return arg in (self.long_name, self.short_name)


class Context(object):
    """
    Parsing context with knowledge of flags & their format.

    Generally associated with the core program or a task.

    When run through a parser, will also hold runtime values filled in by the
    parser.
    """
    def __init__(self):
        self.args = []

    def add_arg(self, *args, **kwargs):
        """
        Adds given ``Argument`` (or constructor args for one) to this context.
        """
        if len(args) == 1 and isinstance(args[0], Argument):
            self.args.append(args[0])
        else:
            self.args.append(Argument(*args, **kwargs))

    def has_arg(self, arg):
        """
        Is this string (``argv`` list member) a valid flag for this context?
        """
        # TODO: maybe just use a dict after all, same value multiple times
        # TODO: this is shitty/brittle/dumb
        try:
            return self.get_arg(arg) is not None
        except ValueError:
            return False

    def get_arg(self, arg):
        match = None
        for argument in self.args:
            if argument.answers_to(arg):
                match = argument
                break
        if match is not None:
            return match
        else:
            raise ValueError, "Argument %r not found" % arg

    def needs_value(self, arg):
        return self.get_arg(arg).needs_value


class Parser(object):
    def __init__(self, initial, contexts=()):
        # TODO: what should contexts be? name-based dict?
        self.initial = initial
        self.contexts = contexts

    def is_flaglike(self, string):
        return re.match(r'^-{1,2}[\w-]+', string)

    def parse_argv(self, argv):
        # Assumes any program name has already been stripped out.
        context = self.initial
        context_index = 0
        flag_index = 0
        for index, arg in enumerate(argv):
            if context.has_arg(arg):
                flag_index = index
            # Otherwise, it's either a flag arg or a task name.
            else:
                flag = argv[flag_index]
                # If previous flag takes an arg, this is the arg
                if context.needs_value(flag):
                    context.set_value(flag, arg)
                # If not, it's the first task name
                else:
                    context = self.contexts[arg]
                    context_index = index
        return self.contexts
