import copy

from ..vendor.lexicon import Lexicon
from ..vendor.fluidity import StateMachine, state, transition

from ..util import debug
from ..exceptions import ParseError


def is_flag(value):
    return value.startswith('-')

def is_long_flag(value):
    return value.startswith('--')


class Parser(object):
    """
    Create parser conscious of ``contexts`` and optional ``initial`` context.

    ``contexts`` should be an iterable of ``Context`` instances which will be
    searched when new context names are encountered during a parse. These
    Contexts determine what flags may follow them, as well as whether given
    flags take values.

    ``initial`` is optional and will be used to determine validity of "core"
    options/flags at the start of the parse run, if any are encountered.

    ``ignore_unknown`` determines what to do when contexts are found which do
    not map to any members of ``contexts``. By default it is ``False``, meaning
    any unknown contexts result in a parse error exception. If ``True``,
    encountering an unknown context halts parsing and populates the return
    value's ``.unparsed`` attribute with the remaining parse tokens.
    """
    def __init__(self, contexts=(), initial=None, ignore_unknown=False):
        self.initial = initial
        self.contexts = Lexicon()
        self.ignore_unknown = ignore_unknown
        for context in contexts:
            debug("Adding {0}".format(context))
            if not context.name:
                raise ValueError("Non-initial contexts must have names.")
            exists = "A context named/aliased {0!r} is already in this parser!"
            if context.name in self.contexts:
                raise ValueError(exists.format(context.name))
            self.contexts[context.name] = context
            for alias in context.aliases:
                if alias in self.contexts:
                    raise ValueError(exists.format(alias))
                self.contexts.alias(alias, to=context.name)

    def parse_argv(self, argv):
        """
        Parse an argv-style token list ``argv``.

        Returns a list of ``Context`` objects matching the order they were
        found in the ``argv`` and containing ``Argument`` objects with updated
        values based on any flags given.

        Assumes any program name has already been stripped out. Good::

            Parser(...).parse_argv(['--core-opt', 'task', '--task-opt'])

        Bad::

            Parser(...).parse_argv(['invoke', '--core-opt', ...])
        """
        machine = ParseMachine(initial=self.initial, contexts=self.contexts,
            ignore_unknown=self.ignore_unknown)
        # FIXME: Why isn't there str.partition for lists? There must be a
        # better way to do this. Split argv around the double-dash remainder
        # sentinel.
        debug("Starting argv: {0!r}".format(argv,))
        try:
            ddash = argv.index('--')
        except ValueError:
            ddash = len(argv) # No remainder == body gets all
        body = argv[:ddash]
        remainder = argv[ddash:][1:] # [1:] to strip off remainder itself
        if remainder:
            debug("Remainder: argv[{0!r}:][1:] => {1!r}".format(
                ddash, remainder
            ))
        for index, token in enumerate(body):
            # Handle non-space-delimited forms, if not currently expecting a
            # flag value and still in valid parsing territory (i.e. not in
            # "unknown" state which implies store-only)
            if not machine.waiting_for_flag_value and is_flag(token) \
                and not machine.result.unparsed:
                orig = token
                # Equals-sign-delimited flags, eg --foo=bar or -f=bar
                if '=' in token:
                    token, _, value = token.partition('=')
                    debug("Splitting x=y expr {0!r} into tokens {1!r} and {2!r}".format( # noqa
                        orig, token, value))
                    body.insert(index + 1, value)
                # Contiguous boolean short flags, e.g. -qv
                elif not is_long_flag(token) and len(token) > 2:
                    full_token = token[:]
                    rest, token = token[2:], token[:2]
                    err = "Splitting {0!r} into token {1!r} and rest {2!r}"
                    debug(err.format(full_token, token, rest))
                    # Handle boolean flag block vs short-flag + value. Make
                    # sure not to test the token as a context flag if we've
                    # passed into 'storing unknown stuff' territory (e.g. on a
                    # core-args pass, handling what are going to be task args)
                    have_flag = (token in machine.context.flags
                        and machine.current_state != 'unknown')
                    if have_flag and machine.context.flags[token].takes_value:
                        debug("{0!r} is a flag for current context & it takes a value, giving it {1!r}".format(token, rest)) # noqa
                        body.insert(index + 1, rest)
                    else:
                        rest = ['-{0}'.format(x) for x in rest]
                        debug("Splitting multi-flag glob {0!r} into {1!r} and {2!r}".format( # noqa
                            orig, token, rest))
                        for item in reversed(rest):
                            body.insert(index + 1, item)
            machine.handle(token)
        machine.finish()
        result = machine.result
        result.remainder = ' '.join(remainder)
        return result


class ParseMachine(StateMachine):
    initial_state = 'context'

    state('context', enter=['complete_flag', 'complete_context'])
    state('unknown', enter=['complete_flag', 'complete_context'])
    state('end', enter=['complete_flag', 'complete_context'])

    transition(
        from_=('context', 'unknown'),
        event='finish',
        to='end',
    )
    transition(
        from_='context',
        event='see_context',
        action='switch_to_context',
        to='context',
    )
    transition(
        from_=('context', 'unknown'),
        event='see_unknown',
        action='store_only',
        to='unknown',
    )

    def changing_state(self, from_, to):
        debug("ParseMachine: {0!r} => {1!r}".format(from_, to))

    def __init__(self, initial, contexts, ignore_unknown):
        # Initialize
        self.ignore_unknown = ignore_unknown
        self.context = copy.deepcopy(initial)
        debug("Initialized with context: {0!r}".format(self.context))
        self.flag = None
        self.result = ParseResult()
        self.contexts = copy.deepcopy(contexts)
        debug("Available contexts: {0!r}".format(self.contexts))
        # In case StateMachine does anything in __init__
        super(ParseMachine, self).__init__()

    @property
    def waiting_for_flag_value(self):
        return (
            self.flag and
            self.flag.takes_value and
            self.flag.raw_value is None
        )

    def handle(self, token):
        debug("Handling token: {0!r}".format(token))
        # Handle unknown state at the top: we don't care about even
        # possibly-valid input if we've encountered unknown input.
        if self.current_state == 'unknown':
            debug("Top-of-handle() see_unknown({0!r})".format(token))
            self.see_unknown(token)
            return
        # Flag
        if self.context and token in self.context.flags:
            debug("Saw flag {0!r}".format(token))
            self.switch_to_flag(token)
        elif self.context and token in self.context.inverse_flags:
            debug("Saw inverse flag {0!r}".format(token))
            self.switch_to_flag(token, inverse=True)
        # Value for current flag
        elif self.waiting_for_flag_value:
            self.see_value(token)
        # Positional args (must come above context-name check in case we still
        # need a posarg and the user legitimately wants to give it a value that
        # just happens to be a valid context name.)
        elif self.context and self.context.needs_positional_arg:
            msg = "Context {0!r} requires positional args, eating {1!r}"
            debug(msg.format(self.context, token))
            self.see_positional_arg(token)
        # New context
        elif token in self.contexts:
            self.see_context(token)
        # Unknown
        else:
            if not self.ignore_unknown:
                debug("Can't find context named {0!r}, erroring".format(token))
                self.error("No idea what {0!r} is!".format(token))
            else:
                debug("Bottom-of-handle() see_unknown({0!r})".format(token))
                self.see_unknown(token)

    def store_only(self, token):
        # Start off the unparsed list
        debug("Storing unknown token {0!r}".format(token))
        self.result.unparsed.append(token)

    def complete_context(self):
        debug("Wrapping up context {0!r}".format(
            self.context.name if self.context else self.context
        ))
        # Ensure all of context's positional args have been given.
        if self.context and self.context.needs_positional_arg:
            err = "'{0}' did not receive all required positional arguments!"
            self.error(err.format(self.context.name))
        if self.context and self.context not in self.result:
            self.result.append(self.context)

    def switch_to_context(self, name):
        self.context = copy.deepcopy(self.contexts[name])
        debug("Moving to context {0!r}".format(name))
        debug("Context args: {0!r}".format(self.context.args))
        debug("Context flags: {0!r}".format(self.context.flags))
        debug("Context inverse_flags: {0!r}".format(
            self.context.inverse_flags
        ))

    def complete_flag(self):
        # Barf if we needed a value and didn't get one
        if (
            self.flag
            and self.flag.takes_value
            and self.flag.raw_value is None
            and not self.flag.optional
        ):
            err = "Flag {0!r} needed value and was not given one!"
            self.error(err.format(self.flag))
        # Handle optional-value flags; at this point they were not given an
        # explicit value, but they were seen, ergo they should get treated like
        # bools.
        if self.flag and self.flag.raw_value is None and self.flag.optional:
            msg = "Saw optional flag {0!r} go by w/ no value; setting to True"
            debug(msg.format(self.flag.name))
            # Skip casting so the bool gets preserved
            self.flag.set_value(True, cast=False)

    def check_ambiguity(self, value):
        """
        Guard against ambiguity when current flag takes an optional value.
        """
        # No flag is currently being examined, or one is but it doesn't take an
        # optional value? Ambiguity isn't possible.
        if not (self.flag and self.flag.optional):
            return False
        # We *are* dealing with an optional-value flag, but it's already
        # received a value? There can't be ambiguity here either.
        debug("Testing flag value: %r" % self.flag.raw_value)
        if self.flag.raw_value is not None:
            return False
        # Otherwise, there *may* be ambiguity if 1 or more of the below tests
        # fail.
        tests = []
        # Unfilled posargs still exist?
        tests.append(self.context and self.context.needs_positional_arg)
        # Value looks like it's supposed to be a flag itself?
        # (Doesn't have to even actually be valid - chances are if it looks
        # like a flag, the user was trying to give one.)
        tests.append(is_flag(value))
        # Value matches another valid task/context name?
        tests.append(value in self.contexts)
        if any(tests):
            msg = "{0!r} is ambiguous when given after an optional-value flag"
            raise ParseError(msg.format(value))

    def switch_to_flag(self, flag, inverse=False):
        # Sanity check for ambiguity w/ prior optional-value flag
        self.check_ambiguity(flag)
        # Set flag/arg obj
        flag = self.context.inverse_flags[flag] if inverse else flag
        # Update state
        self.flag = self.context.flags[flag]
        debug("Moving to flag {0!r}".format(self.flag))
        # Handle boolean flags (which can immediately be updated)
        if not self.flag.takes_value:
            val = not inverse
            debug("Marking seen flag {0!r} as {1}".format(self.flag, val))
            self.flag.value = val

    def see_value(self, value):
        self.check_ambiguity(value)
        if self.flag.takes_value:
            debug("Setting flag {0!r} to value {1!r}".format(self.flag, value))
            self.flag.value = value
        else:
            self.error("Flag {0!r} doesn't take any value!".format(self.flag))

    def see_positional_arg(self, value):
        for arg in self.context.positional_args:
            if arg.value is None:
                arg.value = value
                break

    def error(self, msg):
        raise ParseError(msg, self.context)


class ParseResult(list):
    """
    List-like object with some extra parse-related attributes.

    Specifically, a ``.remainder`` attribute, which is the string found after a
    ``--`` in any parsed argv list; and an ``.unparsed`` attribute, a list of
    tokens that were unable to be parsed.
    """
    def __init__(self, *args, **kwargs):
        super(ParseResult, self).__init__(*args, **kwargs)
        self.remainder = ""
        self.unparsed = []
