import sys

from .loader import Loader
from .parser import Parser, Context, Argument
from .exceptions import Failure, CollectionNotFound
from .util import debug


def parse(argv):
    # Initial/core parsing (core options can affect the rest of the parsing)
    initial_context = Context(args=(
        # TODO: make collection a list-building arg, not a string
        Argument(names=('collection', 'c')),
        Argument(names=('root', 'r')),
        Argument(names=('help', 'h')),
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parser.parse_argv(argv)
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

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
