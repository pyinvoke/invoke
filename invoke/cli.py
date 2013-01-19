import sys

from .loader import Loader
from .parser import Parser, Context, Argument
from .exceptions import Failure, CollectionNotFound, ParseError
from .util import debug, pty_size
from ._version import __version__


def parse_gracefully(parser, argv):
    """
    Run ``parser.parse_argv(argv)`` & gracefully handle ``ParseError``s.

    'Gracefully' meaning to print a useful human-facing error message instead
    of a traceback; the program will still exit if an error is raised.

    If no error is raised, returns the result of the ``parse_argv`` call.
    """
    try:
        return parser.parse_argv(argv)
    except ParseError, e:
        print str(e)
        sys.exit(1)


def parse(argv, collection=None):
    # Initial/core parsing (core options can affect the rest of the parsing)
    initial_context = Context(args=(
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
            help="Show version and exit"
        ),
        Argument(
            names=('list', 'l'),
            kind=bool,
            default=False,
            help="List available tasks."
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
        print "Invoke %s" % __version__
        sys.exit(0)

    # Core --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    # TODO: honor pty size & fill width as needed (with initial indent/offset)
    # TODO: word-wrap help text within its own column
    if args.help.value:
        print "Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]"
        print
        print "Core options:"
        indent = 2
        padding = 3
        tuples = initial_context.help_tuples()
        flag_width = max(map(lambda x: len(x[0]), tuples))
        desc_width = pty_size()[0] - flag_width - indent - padding - 1
        for flag_spec, help_str in tuples:
            flag_padding = flag_width - len(flag_spec)
            print flag_spec + (flag_padding * ' ') + (padding * ' ') + help_str
        print

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
        print "Available tasks:\n"
        print "\n".join(map(lambda x: "    " + x, collection.tasks.keys()))
        print ""
        sys.exit(0)
    return args, collection, tasks


def main():
    # Parse command line
    argv = sys.argv[1:]
    debug("Base argv from sys: %r" % (argv,))
    args, collection, tasks = parse(argv)
    # Take action based on 'core' options and the 'tasks' found
    for context in tasks:
        kwargs = {}
        for name, arg in context.args.iteritems():
            kwargs[name] = arg.value
        try:
            collection[context.name].body(**kwargs)
        except Failure, f:
            sys.exit(f.result.exited)
