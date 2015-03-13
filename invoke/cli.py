from functools import partial
import inspect
import os
import sys
import textwrap

from .vendor import six

from .config import Config
from .loader import FilesystemLoader, DEFAULT_COLLECTION_NAME
from .parser import Parser, ParserContext, Argument
from .executor import Executor
from .exceptions import Failure, CollectionNotFound, ParseError, Exit
from .util import debug, enable_logging
from .platform import pty_size
from ._version import __version__


def task_name_to_key(x):
    return (x.count('.'), x)

sort_names = partial(sorted, key=task_name_to_key)

indent_num = 2
indent = " " * indent_num


def print_columns(tuples):
    """
    Print tabbed columns from (name, help) tuples.

    Useful for listing tasks + docstrings, flags + help strings, etc.
    """
    padding = 3
    # Calculate column sizes: don't wrap flag specs, give what's left over
    # to the descriptions.
    name_width = max(len(x[0]) for x in tuples)
    desc_width = pty_size()[0] - name_width - indent_num - padding - 1
    wrapper = textwrap.TextWrapper(width=desc_width)
    for name, help_str in tuples:
        # Wrap descriptions/help text
        help_chunks = wrapper.wrap(help_str)
        # Print flag spec + padding
        name_padding = name_width - len(name)
        spec = ''.join((
            indent,
            name,
            name_padding * ' ',
            padding * ' '
        ))
        # Print help text as needed
        if help_chunks:
            print(spec + help_chunks[0])
            for chunk in help_chunks[1:]:
                print((' ' * len(spec)) + chunk)
        else:
            print(spec.rstrip())
    print('')


def print_help(argv, initial_context):
    program_name = os.path.basename(argv[0])
    if program_name == 'invoke' or program_name == 'inv':
        program_name = 'inv[oke]'
    print("Usage: {0} [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]".format(program_name)) # noqa
    print("")
    print("Core options:")
    print_columns(initial_context.help_tuples())
    raise Exit


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


def parse(argv, collection=None, version=None):
    """
    Parse ``argv`` list-of-strings into useful core & per-task structures.

    :returns:
        Three-tuple of ``args`` (core, non-task `.Argument` objects),
        ``collection`` (compiled `.Collection` of tasks, using defaults or core
        arguments affecting collection generation) and ``tasks`` (a list of
        `~.ParserContext` objects representing the requested task
        executions).
    """
    # Initial/core parsing (core options can affect the rest of the parsing)
    initial_context = ParserContext(args=(
        Argument(
            names=('no-dedupe',),
            kind=bool,
            default=False,
            help="Disable task deduplication."
        ),
        Argument(
            names=('collection', 'c'),
            help="Specify collection name to load."
        ),
        Argument(
            names=('debug', 'd'),
            kind=bool,
            default=False,
            help="Enable debug output.",
        ),
        Argument(
            names=('echo', 'e'),
            kind=bool,
            default=False,
            help="Echo executed commands before running.",
        ),
        Argument(
            names=('config', 'f'),
            help="Runtime configuration file to use.",
        ),
        Argument(
            names=('help', 'h'),
            optional=True,
            help="Show core or per-task help and exit."
        ),
        Argument(
            names=('hide', 'H'),
            help="Set default value of run()'s 'hide' kwarg.",
        ),
        Argument(
            names=('list', 'l'),
            kind=bool,
            default=False,
            help="List available tasks."
        ),
        Argument(
            names=('pty', 'p'),
            kind=bool,
            default=False,
            help="Use a pty when executing shell commands.",
        ),
        Argument(
            names=('root', 'r'),
            help="Change root directory used for finding task modules."
        ),
        Argument(
            names=('version', 'V'),
            kind=bool,
            default=False,
            help="Show version and exit."
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
    core = parse_gracefully(parser, argv[1:])
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Enable debugging from here on out, if debug flag was given.
    if args.debug.value:
        enable_logging()

    # Print version & exit if necessary
    if args.version.value:
        if version:
            print(version)
        else:
            print("Invoke %s" % __version__)
        raise Exit

    # Core (no value given) --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    if args.help.value is True:
        print_help(argv, initial_context) # exits

    # Load collection (default or specified) and parse leftovers
    start = args.root.value
    loader = FilesystemLoader(start=start)
    coll_name = args.collection.value
    try:
        collection = loader.load(coll_name) if coll_name else loader.load()
    except CollectionNotFound:
        # TODO: improve sys.exit mocking in tests so we can just raise
        # Exit(msg)
        name = coll_name or DEFAULT_COLLECTION_NAME
        six.print_(
            "Can't find any collection named {0!r}!".format(name),
            file=sys.stderr
        )
        raise Exit(1)
    parser = Parser(contexts=collection.to_contexts())
    debug("Parsing tasks against %r" % collection)
    tasks = parse_gracefully(parser, core.unparsed)

    # Per-task help. Use the parser's contexts dict as that's the easiest way
    # to obtain Context objects here - which are what help output needs.
    name = args.help.value
    if name in parser.contexts:
        # Setup
        ctx = parser.contexts[name]
        tuples = ctx.help_tuples()
        docstring = inspect.getdoc(collection[name])
        header = "Usage: inv[oke] [--core-opts] {0} {{0}}[other tasks here ...]".format(name) # noqa
        print(header.format("[--options] " if tuples else ""))
        print("")
        print("Docstring:")
        if docstring:
            # Really wish textwrap worked better for this.
            for line in docstring.splitlines():
                if line.strip():
                    print(indent + line)
                else:
                    print("")
            print("")
        else:
            print(indent + "none")
            print("")
        print("Options:")
        if tuples:
            print_columns(tuples)
        else:
            print(indent + "none")
            print("")
        raise Exit

    # Print discovered tasks if necessary
    if args.list.value:
        # Sort in depth, then alpha, order
        task_names = collection.task_names
        # Short circuit if no tasks to show
        if not task_names:
            msg = "No tasks found in collection '{0}'!"
            print(msg.format(collection.name))
            raise Exit
        pairs = []
        for primary in sort_names(task_names.keys()):
            # Add aliases
            aliases = sort_names(task_names[primary])
            name = primary
            if aliases:
                name += " (%s)" % ', '.join(aliases)
            # Add docstring 1st lines
            task = collection[primary]
            help_ = ""
            if task.__doc__:
                help_ = task.__doc__.lstrip().splitlines()[0]
            pairs.append((name, help_))

        # Print
        print("Available tasks:\n")
        print_columns(pairs)
        raise Exit

    # Print help if:
    # * empty invocation
    # * no default task found in loaded root collection
    # * no other "do an thing" flags were found (implicit in where this code is
    # located - just before return)
    if not tasks and not collection.default:
        print_help(argv, initial_context) # exits

    # Return to caller so they can handle the results
    return args, collection, tasks


def make_config(args, collection):
    """
    Generate a `.Config` object initialized with parser & collection data.

    Specifically, parser-level flags are consulted (typically as a top-level
    "runtime overrides" dict) and the Collection object is used to determine
    where to seek a per-project config file.

    This object is then further updated within `.Executor` with per-task
    configuration values and then told to load the full hierarchy (which
    includes config files.)
    """
    # Low level defaults
    defaults = {
        'run': {
            'warn': False, 'pty': False, 'hide': None, 'echo': False
        },
        'tasks': {'dedupe': True},
    }
    # Set up runtime overrides from flags.
    # NOTE: only fill in values that would alter behavior, otherwise we want
    # the defaults to come through.
    run = {}
    if args['warn-only'].value:
        run['warn'] = True
    if args.pty.value:
        run['pty'] = True
    if args.hide.value:
        run['hide'] = args.hide.value
    if args.echo.value:
        run['echo'] = True
    tasks = {}
    if args['no-dedupe'].value:
        tasks['dedupe'] = False
    overrides = {'run': run, 'tasks': tasks}
    # Stand up config object
    c = Config(
        defaults=defaults,
        overrides=overrides,
        project_home=collection.loaded_from,
        runtime_path=args.config.value,
        env_prefix='INVOKE_',
    )
    return c

def tasks_from_contexts(parser_contexts, collection):
    tasks = []
    for context in parser_contexts:
        tasks.append((context.name, context.as_kwargs))
    # Handle top level default task (like 'make')
    if not tasks:
        tasks = [(collection.default, {})]
    return tasks

def dispatch(argv, version=None):
    try:
        args, collection, parser_contexts = parse(argv, version=version)
    except Exit as e:
        # 'return' here is mostly a concession to testing. Meh :(
        # TODO: probably restructure things better so we don't need this?
        return sys.exit(e.code)
    executor = Executor(collection, make_config(args, collection))
    try:
        tasks = tasks_from_contexts(parser_contexts, collection)
        return executor.execute(*tasks)
    except Failure as f:
        sys.exit(f.result.exited)

def main():
    # Parse command line
    debug("Base argv from sys: %r" % (sys.argv[1:],))
    dispatch(sys.argv)
