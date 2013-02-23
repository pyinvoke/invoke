from functools import partial
import sys
import textwrap

from .vendor import six

from .loader import Loader
from .parser import Parser, Context, Argument
from .executor import Executor
from .exceptions import Failure, CollectionNotFound, ParseError
from .util import debug, pty_size
from ._version import __version__


def depth(name):
    return len(name.split('.'))

def cmp_task_name(a, b):
    return cmp(depth(a), depth(b)) or cmp(a, b)

sort_names = partial(sorted, cmp=cmp_task_name)


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
        Argument(
            names=('no-dedupe',),
            kind=bool,
            default=False,
            help="Disable task deduplication"
        )
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    debug("Parsing initial context (core args)")
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parse_gracefully(parser, argv)
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Print version & exit if necessary
    if args.version.value:
        six.print_("Invoke %s" % __version__)
        sys.exit(0)

    # Core --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    if args.help.value:
        six.print_("Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]")
        six.print_("")
        six.print_("Core options:")
        indent = 2
        padding = 3
        # Calculate column sizes: don't wrap flag specs, give what's left over
        # to the descriptions
        tuples = initial_context.help_tuples()
        flag_width = max(map(lambda x: len(x[0]), tuples))
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
                six.print_(spec + help_chunks[0])
                for chunk in help_chunks[1:]:
                    six.print_((' ' * len(spec)) + chunk)
            else:
                six.print_(spec)
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
        six.print_("Available tasks:\n")
        # Sort in depth, then alpha, order
        task_names = collection.task_names
        names = sort_names(task_names.keys())
        for primary in names:
            aliases = sort_names(task_names[primary])
            out = primary
            if aliases:
                out += " (%s)" % ', '.join(aliases)
            six.print_("    %s" % out)
        six.print_("")
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
            # TODO: allow swapping out of Executor subclasses based on core
            # config options
            # TODO: friggin dashes vs underscores
            Executor(collection).execute(name=context.name, kwargs=kwargs, dedupe=not args['no-dedupe'])
        except Failure, f:
            sys.exit(f.result.exited)
