"""
Command-line completion mechanisms, executed by the core ``--complete`` flag.
"""

import os
import re
import shlex

from ..exceptions import Exit, ParseError
from ..parser import Parser
from ..util import debug, sort_names


def complete(binary, core, initial_context, collection):
    # Strip out program name (scripts give us full command line)
    invocation = re.sub(r'^(%s) ' % binary_selector(binary), '',
                        core.remainder)
    debug("Completing for invocation: {0!r}".format(invocation))
    # Tokenize (shlex will have to do)
    tokens = shlex.split(invocation)
    # Make ourselves a parser (can't just reuse original one as it's mutated /
    # been overwritten)
    parser = Parser(
        initial=initial_context,
        contexts=collection.to_contexts()
    )
    # Handle flags (partial or otherwise)
    if tokens and tokens[-1].startswith('-'):
        tail = tokens[-1]
        debug("Invocation's tail {0!r} is flag-like".format(tail))
        # Gently parse invocation to obtain 'current' context.
        # Use last seen context in case of failure (required for
        # otherwise-invalid partial invocations being completed).
        try:
            debug("Seeking context name in tokens: {0!r}".format(tokens))
            contexts = parser.parse_argv(tokens)
        except ParseError as e:
            debug("Got parser error ({0!r}), grabbing its last-seen context {1!r}".format(e, e.context)) # noqa
            contexts = [e.context]
        # Fall back to core context if no context seen.
        debug("Parsed invocation, contexts: {0!r}".format(contexts))
        if not contexts or not contexts[-1]:
            context = initial_context
        else:
            context = contexts[-1]
        debug("Selected context: {0!r}".format(context))
        # Unknown flags (could be e.g. only partially typed out; could be
        # wholly invalid; doesn't matter) complete with flags.
        debug("Looking for {0!r} in {1!r}".format(tail, context.flags))
        if tail not in context.flags:
            debug("Not found, completing with flag names")
            # Long flags - partial or just the dashes - complete w/ long flags
            if tail.startswith('--'):
                for name in filter(
                    lambda x: x.startswith('--'),
                    context.flag_names()
                ):
                    print(name)
            # Just a dash, completes with all flags
            elif tail == '-':
                for name in context.flag_names():
                    print(name)
            # Otherwise, it's something entirely invalid (a shortflag not
            # recognized, or a java style flag like -foo) so return nothing
            # (the shell will still try completing with files, but that doesn't
            # hurt really.)
            else:
                pass
        # Known flags complete w/ nothing or tasks, depending
        else:
            # Flags expecting values: do nothing, to let default (usually
            # file) shell completion occur (which we actively want in this
            # case.)
            if context.flags[tail].takes_value:
                debug("Found, and it takes a value, so no completion")
                pass
            # Not taking values (eg bools): print task names
            else:
                debug("Found, takes no value, printing task names")
                print_task_names(collection)
    # If not a flag, is either task name or a flag value, so just complete
    # task names.
    else:
        debug("Last token isn't flag-like, just printing task names")
        print_task_names(collection)
    raise Exit


def print_task_names(collection):
    for name in sort_names(collection.task_names):
        print(name)
        # Just stick aliases after the thing they're aliased to. Sorting isn't
        # so important that it's worth bending over backwards here.
        for alias in collection.task_names[name]:
            print(alias)


def print_completion_script(console_type, binary):
    if console_type not in ('bash', 'zsh', 'fish'):
        raise ParseError('Console type "%s" not supported. Choose either '
                         'bash, zsh or fish.')
    path2script = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               console_type)
    debug("Printing completion script from %s" % path2script)
    binary_names = binary_selector(binary).split("|")
    with open(path2script, 'r') as script:
        for line in script.readlines():
            print(line.strip("\n")
                      .replace('inv invoke', ' '.join(binary_names)) # noqa
                      .replace("inv'/'invoke", "'/'".join(binary_names)) # noqa
                      .replace('invoke', binary_names[-1]) # noqa
                      .replace('py%s' % binary_names[-1], 'pyinvoke')) # noqa


def binary_selector(binary):
    """
    Return a selector which can be used in regular expressions
    to match binary name in strings.
    E.g. if you use binary=inv[oke], this gives you 'inv|invoke'.
         if you use binary=fabric, this simply returns 'fabric'.
    """
    m = re.match(r"(\w+)\[?(\w+)?\]?", binary)
    if not m:
        debug("Binary {} could not be matched against our RE.".format(binary))
        return binary
    if m.group(2):
        return "{0}|{0}{1}".format(m.group(1), m.group(2))
    else:
        return m.group(1)
