import sys

from .loader import Loader
from .parser import Parser, Context, Argument
from .exceptions import Failure, CollectionNotFound
from .util import debug


def parse(argv):
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
            help="Show this help message and exit."
        ),
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parser.parse_argv(argv)
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Core --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    # TODO: flexible width
    # TODO: use Clint/etc for indenting
    if args.help.value:
        print "Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]"
        print
        print "Core options:"
        print "\n".join(map(lambda x: "    " + x, initial_context.help_lines()))
        print

    # Load collection (default or specified) and parse leftovers
    loader = Loader(root=args.root.value)
    collection = loader.load_collection(args.collection.value)
    tasks = Parser(contexts=collection.to_contexts()).parse_argv(core.unparsed)

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
