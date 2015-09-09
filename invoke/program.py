import sys

import six

from .cli import *


class Program(object):
    """
    Manages top-level CLI invocation, typically via setup.py entrypoints.

    Designed for distributing Invoke task collections as standalone programs,
    but also used internally to implement the ``invoke`` program itself.

    .. seealso::
        :ref:`reusing-as-a-binary` for a tutorial/walkthrough of this
        functionality.
    """
    def __init__(self, version=None, namespace=None, name=None, binary=None,
        parser_class=Parser, executor_class=Executor):
        """
        Create a new, parameterized `.Program` instance.

        :param str version:
            The program's version, e.g. ``"0.1.0"``. Defaults to ``"unknown"``.

        :param namespace:
            A `.Collection` to use as this program's subcommands.
            
            If ``None`` (the default), the program will behave like ``invoke``,
            seeking a nearby task namespace with a `.Loader` and exposing
            arguments such as :option:`--list` and :option:`--collection` for
            inspecting or selecting specific namespaces.
            
            If given a `.Collection` object, will use it as if it had been
            handed to :option:`--collection`. Will also update the parser to
            remove references to tasks and task-related options, and display
            the subcommands in ``--help`` output. The result will be a program
            that has a static set of subcommands.

        :param str name:
            The program's name, as displayed in ``--version`` output.

            If ``None`` (default), is a capitalized version of the first word
            in the ``argv`` handed to `.run`. For example, when invoked from a
            binstub installed as ``foobar``, it will default to ``Foobar``.

        :param str binary:
            The binary name as displayed in ``--help`` output.

            If ``None`` (default), uses the first word in ``argv`` verbatim (as
            with ``name`` above, except not capitalized).

            Giving this explicitly may be useful when you install your program
            under multiple names, such as Invoke itself does - it installs as
            both ``inv`` and ``invoke``, and sets ``name="inv[oke]"`` so its
            ``--help`` output implies both names.

        :param parser_class:
            The CLI-parsing class to use for parsing the command line. Must be
            `.Parser` or implement the same interface. Defaults to `.Parser`.

        :param executor_class:
            The task-executing class to use for executing any tasks found on
            the command line. Must be `.Executor` or implement the same
            interface. Defaults to `.Executor`.
        """
        self.version = "unknown" if version is None else version
        self.namespace = namespace
        self.name = name
        self.binary = binary
        self.parser_class = parser_class
        self.executor_class = executor_class

    def run(self, argv):
        """
        Execute main CLI logic, based on ``argv``.

        :param argv:
            The arguments to execute against. May be ``None``, a list of
            strings, or a string. See `.normalize_argv` for details.
        """
        argv = self.normalize_argv(argv)
        try:
            args, collection, parser_contexts = self.parse(argv)
        except Exit as e:
            # 'return' here is mostly a concession to testing. Meh :(
            # TODO: probably restructure things better so we don't need this?
            return sys.exit(e.code)
        executor = self.executor_class(
            collection, make_config(args, collection)
        )
        try:
            tasks = tasks_from_contexts(parser_contexts, collection)
            executor.execute(*tasks)
        except Failure as f:
            sys.exit(f.result.exited)

    def normalize_argv(self, argv):
        """
        Massages ``argv`` into a useful list of strings.

        **If None** (the default), uses `sys.argv` itself.

        **If a non-string iterable**, uses that in place of `sys.argv`.

        **If a string**, performs a `str.split` and then executes with the
        result. (This is mostly a convenience; when in doubt, use a list.)
        """
        if argv is None:
            argv = sys.argv
        elif isinstance(argv, six.string_types):
            argv = argv.split()
        return argv


    def parse(self, argv, collection=None, version=None):
        """
        Parse ``argv`` list-of-strings into useful core & per-task structures.

        :returns:
            Three-tuple of ``args`` (core, non-task `.Argument` objects),
            ``collection`` (compiled `.Collection` of tasks, using defaults or
            core arguments affecting collection generation) and ``tasks`` (a
            list of `~.ParserContext` objects representing the requested task
            executions).
        """
        # Initial/core parsing (core options can affect the rest of the
        # parsing)
        initial_context = ParserContext(args=(
            Argument(
                names=('complete',),
                kind=bool,
                default=False,
                help="Print tab-completion candidates for given parse remainder.", # noqa
            ),
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
        msg = "After core-args pass, leftover argv: {0!r}"
        debug(msg.format(core.unparsed))
        args = core[0].args

        # Enable debugging from here on out, if debug flag was given.
        if args.debug.value:
            enable_logging()

        # Print version & exit if necessary
        if args.version.value:
            if version:
                print(version)
            else:
                print("Invoke {0}".format(__version__))
            raise Exit

        # Core (no value given) --help output
        # TODO: if this wants to display context sensitive help (e.g. a combo
        # help and available tasks listing; or core flags modified by
        # plugins/task modules) it will have to move farther down.
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
        debug("Parsing tasks against {0!r}".format(collection))
        tasks = parse_gracefully(parser, core.unparsed)

        # Per-task help. Use the parser's contexts dict as that's the easiest
        # way to obtain Context objects here - which are what help output
        # needs.
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
            for primary in sort_names(task_names):
                # Add aliases
                aliases = sort_names(task_names[primary])
                name = primary
                if aliases:
                    name += " ({0})".format(', '.join(aliases))
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

        # Print completion helpers if necessary
        if args.complete.value:
            complete(core, initial_context, collection)

        # Print help if:
        # * empty invocation
        # * no default task found in loaded root collection
        # * no other "do an thing" flags were found (implicit in where this
        #   code is located - just before return)
        if not tasks and not collection.default:
            print_help(argv, initial_context) # exits

        # Return to caller so they can handle the results
        return args, collection, tasks
