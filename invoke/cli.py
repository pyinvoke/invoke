from functools import partial
import sys
import textwrap

from .vendor import six

from .context import Context
from .loader import Loader
from .parser import Parser, Context as ParserContext, Argument
from .executor import Executor
from .exceptions import Failure, CollectionNotFound, ParseError
from .util import debug, pty_size
from ._version import __version__


def task_name_to_key(x):
    return (x.count('.'), x)

sort_names = partial(sorted, key=task_name_to_key)


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
            kind=bool,
            default=False,
            help="Show this help message and exit."
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
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    debug("Parsing initial context (core args)")
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parse_gracefully(parser, argv)
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Print version & exit if necessary
    if args.version.value:
        print("Invoke %s" % __version__)
        sys.exit(0)

    # Core --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    if args.help.value:
        print("Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]")
        print("")
        print("Core options:")
        indent = 2
        padding = 3
        # Calculate column sizes: don't wrap flag specs, give what's left over
        # to the descriptions.
        tuples = initial_context.help_tuples()
        flag_width = max(len(x[0]) for x in tuples)
        desc_width = pty_size()[0] - flag_width - indent - padding - 1
        wrapper = textwrap.TextWrapper(width=desc_width)
        for flag_spec, help_str in tuples:
            # Wrap descriptions/help text
            help_chunks = wrapper.wrap(help_str)
            # Print flag spec + padding
            flag_padding = flag_width - len(flag_spec)
            spec = ''.join((
                indent * ' ',
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
        sys.exit(0)

    # Load collection (default or specified) and parse leftovers
    # (Skip loading if somebody gave us an explicit task collection.)
    if not collection:
        debug("No collection given, loading from %r" % args.root.value)
        loader = Loader(root=args.root.value)
        collection = loader.load_collection(args.collection.value)
    parser = Parser(contexts=collection.to_contexts())
    debug("Parsing actual tasks against collection %r" % collection)
    tasks = parse_gracefully(parser, core.unparsed)

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
            print("    %s" % out)
        print("")
        sys.exit(0)

    # Return to caller so they can handle the results
    return args, collection, tasks


def derive_opts(args):
    run = {}
    # FIXME: deal with dash to underscore
    if args['warn-only']:
        run['warn'] = True
    return {'run': run}

def dispatch(argv):
    args, collection, tasks = parse(argv)
    results = []
    executor = Executor(collection, Context(**derive_opts(args)))
    # Take action based on 'core' options and the 'tasks' found
    for context in tasks:
        kwargs = {}
        for name, arg in six.iteritems(context.args):
            kwargs[name] = arg.value
        try:
            # TODO: allow swapping out of Executor subclasses based on core
            # config options
            # FIXME: friggin dashes vs underscores
            results.append(executor.execute(
                name=context.name,
                kwargs=kwargs,
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
