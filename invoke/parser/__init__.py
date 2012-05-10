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
        current_flag = None
        debug("Parsing argv %r" % (argv,))
        debug("Starting with context %s" % context)
        for index, arg in enumerate(argv):
            debug("Testing string arg %r at index %r" % (arg, index))
            if context.has_arg(arg):
                debug("Current context has this as a flag")
                current_flag = context.get_arg(arg)
            # Otherwise, it's either a flag arg or a task name.
            else:
                # TODO: this needs to be the Argument obj
                debug("Current context does not have this as a flag")
                # If previous flag takes an arg, this is the arg
                # TODO: this needs to test the Argument obj
                if current_flag and current_flag.needs_value:
                    debug("Previous flag needed a value, this is it")
                    # TODO: type coercion? or should that happen on access
                    # (probably yes)
                    current_flag.set_value(arg)
                # If not, it's the first task name (or invalid)
                else:
                    debug("That pevious flag needs no value")
                    # TODO: how best to associate task name with contexts?
                    # (esp given a task can have N names)
                    # TODO: brings in the usual question of the root ctx
                    if arg in [x.name for x in self.contexts]:
                        debug("Looks like a valid task name")
                        context = self.contexts[arg]
                        context_index = index
                    else:
                        # TODO: what error to raise?
                        debug("Not a flag, a flag arg or a task: invalid")
                        raise ValueError("lol")
        return self.contexts
