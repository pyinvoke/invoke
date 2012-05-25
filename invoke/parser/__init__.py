from lexicon import Lexicon

from .context import Context
from .argument import Argument # Mostly for importing via invoke.parser.<x>
from ..util import debug


class Parser(object):
    def __init__(self, initial, contexts=()):
        self.initial = initial
        self.contexts = Lexicon()
        for context in contexts:
            debug("Adding context %s" % context)
            if not context.name:
                raise ValueError("Non-initial contexts must have names.")
            self.contexts[context.name] = context
            for alias in context.aliases:
                self.contexts.alias(alias, to=context.name)

    def parse_argv(self, argv):
        """
        Parse an argv-style token list ``argv``.

        Returns an ordered list of ``ParsedContext`` objects.

        Assumes any program name has already been stripped out. Good::

            Parser(...).parse_argv(['--core-opt', 'task', '--task-opt'])

        Bad::

            Parser(...).parse_argv(['invoke', '--core-opt', ...])
        """
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
                debug("Current context does not have this as a flag")
                # If currently being handled flag takes an arg, this should be
                # it.
                # TODO: can we handle the case where somebody forgot the value?
                # I.e. if they try to do invoke --needs-arg --lol, and --lol is
                # a valid flag, should we error?
                if current_flag and current_flag.needs_value:
                    debug("Previous flag needed a value, this is it")
                    # TODO: type coercion? or should that happen on access
                    # (probably yes)
                    current_flag.set_value(arg)
                # If not, it's the first task name (or invalid)
                else:
                    debug("Not currently looking for a flag arg, or no flag context")
                    debug("Current contexts: %r" % self.contexts)
                    if arg in self.contexts:
                        debug("Looks like a valid task name")
                        context = self.contexts[arg]
                        context_index = index
                    else:
                        # TODO: what error to raise?
                        debug("Not a flag, a flag arg or a task: invalid")
                        raise ValueError("lol")
        return self.contexts
