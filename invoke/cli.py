from functools import partial
import sys
import textwrap

from .vendor import six

from .context import Context
from .loader import FilesystemLoader
from .parser import Parser, Context as ParserContext, Argument
from .executor import Executor
from .exceptions import Failure, CollectionNotFound, ParseError
from .util import debug, pty_size, enable_logging
from ._version import __version__


def task_name_to_key(x):
    return (x.count('.'), x)

sort_names = partial(sorted, key=task_name_to_key)

indent_num = 2
indent = " " * indent_num


def print_help(tuples):
    padding = 3
    # Calculate column sizes: don't wrap flag specs, give what's left over
    # to the descriptions.
    flag_width = max(len(x[0]) for x in tuples)
    desc_width = pty_size()[0] - flag_width - indent_num - padding - 1
    wrapper = textwrap.TextWrapper(width=desc_width)
    for flag_spec, help_str in tuples:
        # Wrap descriptions/help text
        help_chunks = wrapper.wrap(help_str)
        # Print flag spec + padding
        flag_padding = flag_width - len(flag_spec)
        spec = ''.join((
            indent,
            flag_spec,
            flag_padding * ' ',
            padding * ' '
        ))
        # Print help text as needed
        if help_chunks:
            print(spec + help_chunks[0])
            for chunk in help_chunks[1:]:
                print((' ' * len(spec)) + chunk)
        else:
            print(spec)
    print('')



def parse_gracefully(parser, argv):
    """
    Run ``parser.parse_argv(argv)`` & gracefully handle ``ParseError``.

    'Gracefully' meaning to print a useful human-facing error message instead
    of a traceback; the program will still exit if an error is raised.

    If no error is raised, returns the result of the ``parse_argv`` call.
    """
    try:
        return parser.parse_argv(argv)
    except ParseError as e:
        sys.exit(str(e))


def parse(argv, collection=None):
    """
    Parse ``argv`` list-of-strings into useful core & per-task structures.

    :returns:
        Three-tuple of ``args`` (core, non-task `.Argument` objects),
        ``collection`` (compiled `.Collection` of tasks, using defaults or core
        arguments affecting collection generation) and ``tasks`` (a list of
        `~.parser.context.Context` objects representing the requested task
        executions).
    """
    # Initial/core parsing (core options can affect the rest of the parsing)
    initial_context = ParserContext(args=(
        # TODO: make '--collection' a list-building arg, not a string
        Argument(
            names=('collection', 'c'),
            help="Specify collection name to load. May be given >1 time."
        ),
        Argument(
            names=('root', 'r'),
            help="Change root directory used for finding task modules."
        ),
        Argument(
            names=('help', 'h'),
            optional=True,
            help="Show core or per-task help and exit."
        ),
        Argument(
            names=('version', 'V'),
            kind=bool,
            default=False,
            help="Show version and exit."
        ),
        Argument(
            names=('list', 'l'),
            kind=bool,
            default=False,
            help="List available tasks."
        ),
        Argument(
            names=('no-dedupe',),
            kind=bool,
            default=False,
            help="Disable task deduplication."
        ),
        Argument(
            names=('echo', 'e'),
            kind=bool,
            default=False,
            help="Echo executed commands before running.",
        ),
        Argument(
            names=('warn-only', 'w'),
            kind=bool,
            default=False,
            help="Warn, instead of failing, when shell commands fail.",
        ),
        Argument(
            names=('pty', 'p'),
            kind=bool,
            default=False,
            help="Use a pty when executing shell commands.",
        ),
        Argument(
            names=('hide', 'H'),
            help="Set default value of run()'s 'hide' kwarg.",
        ),
        Argument(
            names=('debug', 'd'),
            kind=bool,
            default=False,
            help="Enable debug output.",
        ),
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    debug("Parsing initial context (core args)")
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parse_gracefully(parser, argv)
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Enable debugging from here on out, if debug flag was given.
    if args.debug.value:
        enable_logging()

    # Print version & exit if necessary
    if args.version.value:
        print("Invoke %s" % __version__)
        sys.exit(0)

    # Core (no value given) --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    if args.help.value == True:
        print("Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]")
        print("")
        print("Core options:")
        print_help(initial_context.help_tuples())
        sys.exit(0)

    # Load collection (default or specified) and parse leftovers
    # (Skip loading if somebody gave us an explicit task collection.)
    if not collection:
        debug("No collection given, loading from %r" % args.root.value)
        loader = FilesystemLoader(start=args.root.value)
        start = args.collection.value
        collection = loader.load(start) if start else loader.load()
    parser = Parser(contexts=collection.to_contexts())
    debug("Parsing actual tasks against collection %r" % collection)
    tasks = parse_gracefully(parser, core.unparsed)

    # Per-task help. Use the parser's contexts dict as that's the easiest way
    # to obtain Context objects here - which are what help output needs.
    name = args.help.value
    if name in parser.contexts:
        # Setup
        ctx = parser.contexts[name]
        tuples = ctx.help_tuples()
        docstring = collection[name].__doc__
        header = "Usage: inv[oke] [--core-opts] %s %%s[other tasks here ...]" % name
        print(header % ("[--options] " if tuples else ""))
        print("")
        print("Docstring:")
        if docstring:
            # Really wish textwrap worked better for this.
            doclines = docstring.lstrip().splitlines()
            for line in doclines:
                print(indent + textwrap.dedent(line))
            # Print trailing blank line if docstring didn't end with one
            if textwrap.dedent(doclines[-1]):
                print("")
        else:
            print(indent + "none")
            print("")
        print("Options:")
        if tuples:
            print_help(tuples)
        else:
            print(indent + "none")
            print("")
        sys.exit(0)

    # Print discovered tasks if necessary
    if args.list.value:
        print("Available tasks:\n")
        # Sort in depth, then alpha, order
        task_names = collection.task_names
        names = sort_names(task_names.keys())
        for primary in names:
            aliases = sort_names(task_names[primary])
            out = primary
            if aliases:
                out += " (%s)" % ', '.join(aliases)
            print("  %s" % out)
        print("")
        sys.exit(0)

    # Return to caller so they can handle the results
    return args, collection, tasks


def derive_opts(args):
    run = {}
    if args['warn-only'].value:
        run['warn'] = True
    if args.pty.value:
        run['pty'] = True
    if args.hide.value:
        run['hide'] = args.hide.value
    if args.echo.value:
        run['echo'] = True
    return {'run': run}

def dispatch(argv):
    args, collection, tasks = parse(argv)
    results = []
    executor = Executor(collection, Context(**derive_opts(args)))
    # Take action based on 'core' options and the 'tasks' found
    for context in tasks:
        kwargs = {}
        # Take CLI arguments out of parser context, create func-kwarg dict.
        for _, arg in six.iteritems(context.args):
            # Use the arg obj's internal name - not what was necessarily given
            # on the CLI. (E.g. --my-option vs --my_option for
            # mytask(my_option=xxx) requires this.)
            # TODO: store 'given' name somewhere in case somebody wants to see
            # it when handling args.
            kwargs[arg.name] = arg.value
        try:
            # TODO: allow swapping out of Executor subclasses based on core
            # config options
            results.append(executor.execute(
                # Task name given on CLI
                name=context.name,
                # Flags/other args given to this task specifically
                kwargs=kwargs,
                # Was the core dedupe flag given?
                dedupe=not args['no-dedupe']
            ))
        except Failure as f:
            sys.exit(f.result.exited)
    return results


def main():
    # Parse command line
    argv = sys.argv[1:]
    debug("Base argv from sys: %r" % (argv,))
    dispatch(argv)
