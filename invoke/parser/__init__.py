from .context import Context
from .argument import Argument # Mostly for importing via invoke.parser.<x>
from ..util import debug


class Parser(object):
    def __init__(self, initial, contexts=()):
        # TODO: what should contexts be? name-based dict?
        self.initial = initial
        self.contexts = contexts

    def parse_argv(self, argv):
        # Assumes any program name has already been stripped out.
        context = self.initial
        context_index = 0
        flag_index = 0
        debug("Parsing argv %r" % (argv,))
        debug("Starting with context %s" % context)
        for index, arg in enumerate(argv):
            debug("Testing string arg %r at index %r" % (arg, index))
            if context.has_arg(arg):
                flag_index = index
                debug("Current context has this as a flag")
            # Otherwise, it's either a flag arg or a task name.
            else:
                flag = argv[flag_index]
                debug("Current context does not have this as a flag")
                # If previous flag takes an arg, this is the arg
                if context.needs_value(flag):
                    context.set_value(flag, arg)
                # If not, it's the first task name
                else:
                    context = self.contexts[arg]
                    context_index = index
                    debug("That pevious flag needs no value")
        return self.contexts
