from __future__ import unicode_literals, print_function

import inspect
import os
import sys
import textwrap

from .util import six

from . import Collection, Config, Executor, FilesystemLoader
from .complete import complete
from .parser import Parser, ParserContext, Argument
from .exceptions import (
    UnexpectedExit, CollectionNotFound, ParseError, Exit,
)
from .terminals import pty_size
from .util import debug, enable_logging, sort_names, helpline


class Program(object):
    """
    Manages top-level CLI invocation, typically via ``setup.py`` entrypoints.

    Designed for distributing Invoke task collections as standalone programs,
    but also used internally to implement the ``invoke`` program itself.

    .. seealso::
        :ref:`reusing-as-a-binary` for a tutorial/walkthrough of this
        functionality.
    """
    def core_args(self):
        """
        Return default core `.Argument` objects, as a list.
        """
        # Arguments present always, even when wrapped as a different binary
        return [
            Argument(
                names=('complete',),
                kind=bool,
                default=False,
                help="Print tab-completion candidates for given parse remainder.", # noqa
            ),
            Argument(
                names=('debug', 'd'),
                kind=bool,
                default=False,
                help="Enable debug output.",
            ),
            Argument(
                names=('write-pyc',),
                kind=bool,
                default=False,
                help="Enable creation of .pyc files.",
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
                names=('hide',),
                help="Set default value of run()'s 'hide' kwarg.",
            ),
            Argument(
                names=('list', 'l'),
                optional=True,
                help="List available tasks, optionally limited to a namespace."
            ),
            Argument(
                names=('list-depth', 'D'),
                kind=int,
                default=0,
                help="When listing tasks, only show the first INT levels.",
            ),
            Argument(
                names=('list-format', 'F'),
                help="Change the display format used when listing tasks. Should be one of: flat (default), nested, json.", # noqa
                default='flat',
            ),
            Argument(
                names=('pty', 'p'),
                kind=bool,
                default=False,
                help="Use a pty when executing shell commands.",
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
        ]

    def task_args(self):
        """
        Return default task-related `.Argument` objects, as a list.

        These are only added to the core args in "task runner" mode (the
        default for ``invoke`` itself) - they are omitted when the constructor
        is given a non-empty ``namespace`` argument ("bundled namespace" mode).
        """
        # Arguments pertaining specifically to invocation as 'invoke' itself
        # (or as other arbitrary-task-executing programs, like 'fab')
        return [
            Argument(
                names=('collection', 'c'),
                help="Specify collection name to load."
            ),
            Argument(
                names=('no-dedupe',),
                kind=bool,
                default=False,
                help="Disable task deduplication."
            ),
            Argument(
                names=('search-root', 'r'),
                help="Change root directory used for finding task modules."
            ),
        ]

    # Other class-level global variables a subclass might override sometime
    # maybe?
    leading_indent_width = 2
    leading_indent = " " * leading_indent_width
    indent_width = 4
    indent = " " * indent_width
    col_padding = 3

    def __init__(self,
        version=None,
        namespace=None,
        name=None,
        binary=None,
        loader_class=None,
        executor_class=None,
        config_class=None,
    ):
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
            both ``inv`` and ``invoke``, and sets ``binary="inv[oke]"`` so its
            ``--help`` output implies both names.

        :param loader_class:
            The `.Loader` subclass to use when loading task collections.

            Defaults to `.FilesystemLoader`.

        :param executor_class:
            The `.Executor` subclass to use when executing tasks.

            Defaults to `.Executor`.

        :param config_class:
            The `.Config` subclass to use for the base config object.

            Defaults to `.Config`.
        """
        self.version = "unknown" if version is None else version
        self.namespace = namespace
        self._name = name
        self._binary = binary
        self.argv = None
        self.loader_class = loader_class or FilesystemLoader
        self.executor_class = executor_class or Executor
        self.config_class = config_class or Config

    def create_config(self):
        """
        Instantiate a `.Config` (or subclass, depending) for use in task exec.

        This Config is fully usable but will lack runtime-derived data like
        project & runtime config files, CLI arg overrides, etc. That data is
        added later in `update_config`. See `.Config` docstring for lifecycle
        details.

        :returns: ``None``; sets ``self.config`` instead.
        """
        self.config = self.config_class()

    def update_config(self, merge=True):
        """
        Update the previously instantiated `.Config` with parsed data.

        For example, this is how ``--echo`` is able to override the default
        config value for ``run.echo``.

        :param bool merge:
            Whether to merge at the end, or defer. Primarily useful for
            subclassers. Default: ``True``.
        """
        # Now that we have parse results handy, we can grab the remaining
        # config bits:
        # - runtime config, as it is dependent on the runtime flag
        # - the overrides config level, as it is composed of runtime flag data
        # NOTE: only fill in values that would alter behavior, otherwise we
        # want the defaults to come through.
        run = {}
        if self.args['warn-only'].value:
            run['warn'] = True
        if self.args.pty.value:
            run['pty'] = True
        if self.args.hide.value:
            run['hide'] = self.args.hide.value
        if self.args.echo.value:
            run['echo'] = True
        tasks = {}
        if 'no-dedupe' in self.args and self.args['no-dedupe'].value:
            tasks['dedupe'] = False
        self.config.load_overrides({'run': run, 'tasks': tasks}, merge=False)
        self.config.set_runtime_path(self.args.config.value)
        self.config.load_runtime(merge=False)
        if merge:
            self.config.merge()

    def run(self, argv=None, exit=True):
        """
        Execute main CLI logic, based on ``argv``.

        :param argv:
            The arguments to execute against. May be ``None``, a list of
            strings, or a string. See `.normalize_argv` for details.

        :param bool exit:
            When ``True`` (default: ``False``), will ignore `.ParseError`,
            `.Exit` and `.Failure` exceptions, which otherwise trigger calls to
            `sys.exit`.

            .. note::
                This is mostly a concession to testing. If you're setting this
                to ``True`` in a production setting, you should probably be
                using `.Executor` and friends directly instead!
        """
        try:
            # Create an initial config, which will hold defaults & values from
            # most config file locations (all but runtime.) Used to inform
            # loading & parsing behavior.
            self.create_config()
            # Parse the given ARGV with our CLI parsing machinery, resulting in
            # things like self.args (core args/flags), self.collection (the
            # loaded namespace, which may be affected by the core flags) and
            # self.tasks (the tasks requested for exec and their own
            # args/flags)
            self.parse_core(argv)
            # Handle collection concerns including project config
            self.parse_collection()
            # Parse remainder of argv as task-related input
            self.parse_tasks()
            # End of parsing (typically bailout stuff like --list, --help)
            self.parse_cleanup()
            # Update the earlier Config with new values from the parse step -
            # runtime config file contents and flag-derived overrides (e.g. for
            # run()'s echo, warn, etc options.)
            self.update_config()
            # Create an Executor, passing in the data resulting from the prior
            # steps, then tell it to execute the tasks.
            self.execute()
        except (UnexpectedExit, Exit, ParseError) as e:
            debug("Received a possibly-skippable exception: {!r}".format(e))
            # Print error messages from parser, runner, etc if necessary;
            # prevents messy traceback but still clues interactive user into
            # problems.
            if isinstance(e, ParseError):
                print(e, file=sys.stderr)
            if isinstance(e, UnexpectedExit) and e.result.hide:
                print(e, file=sys.stderr, end='')
            # Terminate execution unless we were told not to.
            if exit:
                if isinstance(e, UnexpectedExit):
                    code = e.result.exited
                elif isinstance(e, Exit):
                    code = e.code
                elif isinstance(e, ParseError):
                    code = 1
                sys.exit(code)
            else:
                debug("Invoked as run(..., exit=False), ignoring exception")
        except KeyboardInterrupt:
            sys.exit(1) # Same behavior as Python itself outside of REPL

    def parse_core(self, argv):
        debug("argv given to Program.run: {!r}".format(argv))
        self.normalize_argv(argv)

        # Obtain core args (sets self.core)
        self.parse_core_args()
        debug("Finished parsing core args")

        # Set interpreter bytecode-writing flag
        sys.dont_write_bytecode = not self.args['write-pyc'].value

        # Enable debugging from here on out, if debug flag was given.
        # (Prior to this point, debugging requires setting INVOKE_DEBUG).
        if self.args.debug.value:
            enable_logging()

        # Print version & exit if necessary
        if self.args.version.value:
            debug("Saw --version, printing version & exiting")
            self.print_version()
            raise Exit

    def parse_collection(self):
        """
        Load a tasks collection & project-level config.
        """
        # Load a collection of tasks unless one was already set.
        if self.namespace is not None:
            debug("Program was given a default namespace, skipping collection loading") # noqa
            self.collection = self.namespace
        else:
            debug("No default namespace provided, trying to load one from disk") # noqa
            # If no bundled namespace & --help was given, just print it and
            # exit. (If we did have a bundled namespace, core --help will be
            # handled *after* the collection is loaded & parsing is done.)
            if self.args.help.value is True:
                debug("No bundled namespace & bare --help given; printing help and exiting.") # noqa
                self.print_help()
                raise Exit
            self.load_collection()

        # TODO: load project conf, if possible, gracefully

    def parse_cleanup(self):
        """
        Post-parsing, pre-execution steps such as --help, --list, etc.
        """
        halp = self.args.help.value or self.core_via_tasks.args.help.value

        # Core (no value given) --help output (only when bundled namespace)
        if halp is True:
            debug("Saw bare --help, printing help & exiting")
            self.print_help()
            raise Exit

        # Print per-task help, if necessary
        if halp:
            if halp in self.parser.contexts:
                msg = "Saw --help <taskname>, printing per-task help & exiting"
                debug(msg)
                self.print_task_help(halp)
                raise Exit
            else:
                # TODO: feels real dumb to factor this out of Parser, but...we
                # should?
                raise ParseError("No idea what '{}' is!".format(halp))

        # Print discovered tasks if necessary
        list_root = self.args.list.value # will be True or string
        list_format = self.args['list-format'].value
        # TODO: work in depth
        if list_root:
            self.list_tasks(
                root=list_root,
                format_=list_format,
            )
            raise Exit

        # Print completion helpers if necessary
        if self.args.complete.value:
            complete(self.core, self.initial_context, self.collection)

        # Fallback behavior if no tasks were given & no default specified
        # (mostly a subroutine for overriding purposes)
        # NOTE: when there is a default task, Executor will select it when no
        # tasks were found in CLI parsing.
        if not self.tasks and not self.collection.default:
            self.no_tasks_given()

    def no_tasks_given(self):
        debug("No tasks specified for execution and no default task; printing global help as fallback") # noqa
        self.print_help()
        raise Exit

    def execute(self):
        """
        Hand off data & tasks-to-execute specification to an `.Executor`.

        .. note::
            Client code just wanting a different `.Executor` subclass can just
            set ``executor_class`` in `.__init__`.
        """
        executor = self.executor_class(self.collection, self.config, self.core)
        executor.execute(*self.tasks)

    def normalize_argv(self, argv):
        """
        Massages ``argv`` into a useful list of strings.

        **If None** (the default), uses `sys.argv`.

        **If a non-string iterable**, uses that in place of `sys.argv`.

        **If a string**, performs a `str.split` and then executes with the
        result. (This is mostly a convenience; when in doubt, use a list.)

        Sets ``self.argv`` to the result.
        """
        if argv is None:
            argv = sys.argv
            debug("argv was None; using sys.argv: {!r}".format(argv))
        elif isinstance(argv, six.string_types):
            argv = argv.split()
            debug("argv was string-like; splitting: {!r}".format(argv))
        self.argv = argv

    @property
    def name(self):
        """
        Derive program's human-readable name based on `.binary`.
        """
        return self._name or self.binary.capitalize()

    @property
    def binary(self):
        """
        Derive program's help-oriented binary name(s) from init args & argv.
        """
        return self._binary or os.path.basename(self.argv[0])

    @property
    def args(self):
        """
        Obtain core program args from ``self.core`` parse result.
        """
        return self.core[0].args

    @property
    def initial_context(self):
        """
        The initial parser context, aka core program flags.

        The specific arguments contained therein will differ depending on
        whether a bundled namespace was specified in `.__init__`.
        """
        args = self.core_args()
        if self.namespace is None:
            args += self.task_args()
        return ParserContext(args=args)

    def print_version(self):
        print("{} {}".format(self.name, self.version or "unknown"))

    def print_help(self):
        usage_suffix = "task1 [--task1-opts] ... taskN [--taskN-opts]"
        if self.namespace is not None:
            usage_suffix = "<subcommand> [--subcommand-opts] ..."
        print("Usage: {} [--core-opts] {}".format(self.binary, usage_suffix))
        print("")
        print("Core options:")
        print("")
        self.print_columns(self.initial_context.help_tuples())
        if self.namespace is not None:
            self.list_tasks()

    def parse_core_args(self):
        """
        Filter out core args, leaving any tasks or their args for later.

        Sets ``self.core`` to the `.ParseResult` from this step.
        """
        debug("Parsing initial context (core args)")
        parser = Parser(initial=self.initial_context, ignore_unknown=True)
        self.core = parser.parse_argv(self.argv[1:])
        msg = "Core-args parse result: {!r} & unparsed: {!r}"
        debug(msg.format(self.core, self.core.unparsed))

    def load_collection(self):
        """
        Load a task collection based on parsed core args, or die trying.
        """
        # NOTE: start, coll_name both fall back to configuration values within
        # Loader (which may, however, get them from our config.)
        start = self.args['search-root'].value
        loader = self.loader_class(config=self.config, start=start)
        coll_name = self.args.collection.value
        try:
            module, parent = loader.load(coll_name)
            # This is the earliest we can load project config, so we should -
            # allows project config to affect the task parsing step!
            # TODO: is it worth merging these set- and load- methods? May
            # require more tweaking of how things behave in/after __init__.
            self.config.set_project_location(parent)
            self.config.load_project()
            self.collection = Collection.from_module(
                module,
                loaded_from=parent,
                auto_dash_names=self.config.tasks.auto_dash_names,
            )
        except CollectionNotFound as e:
            six.print_(
                "Can't find any collection named {!r}!".format(e.name),
                file=sys.stderr
            )
            raise Exit(1)

    def parse_tasks(self):
        """
        Parse leftover args, which are typically tasks & per-task args.

        Sets ``self.parser`` to the parser used, ``self.tasks`` to the
        parsed per-task contexts, and ``self.core_via_tasks`` to a context
        holding any core flags seen within the task contexts.
        """
        self.parser = Parser(
            initial=self.initial_context,
            contexts=self.collection.to_contexts(),
        )
        debug("Parsing tasks against {!r}".format(self.collection))
        result = self.parser.parse_argv(self.core.unparsed)
        # TODO: can we easily 'merge' this into self.core? Ehh
        self.core_via_tasks = result.pop(0)
        self.tasks = result
        debug("Resulting task contexts: {!r}".format(self.tasks))

    def print_task_help(self, name):
        """
        Print help for a specific task, e.g. ``inv --help <taskname>``.
        """
        # Setup
        ctx = self.parser.contexts[name]
        tuples = ctx.help_tuples()
        docstring = inspect.getdoc(self.collection[name])
        header = "Usage: {} [--core-opts] {} {}[other tasks here ...]"
        opts = "[--options] " if tuples else ""
        print(header.format(self.binary, name, opts))
        print("")
        print("Docstring:")
        if docstring:
            # Really wish textwrap worked better for this.
            for line in docstring.splitlines():
                if line.strip():
                    print(self.leading_indent + line)
                else:
                    print("")
            print("")
        else:
            print(self.leading_indent + "none")
            print("")
        print("Options:")
        if tuples:
            self.print_columns(tuples)
        else:
            print(self.leading_indent + "none")
            print("")

    def list_tasks(self, root=None, format_='flat'):
        # TODO: honor depth
        # TODO: honor root
        # Short circuit if no tasks to show (Collection now implements bool)
        if not self.collection:
            msg = "No tasks found in collection '{}'!"
            print(msg.format(self.collection.name))
            raise Exit
        strategy = getattr(self, "list_{}".format(format_))
        strategy(root=root)

    def display_with_columns(self, pairs, extra=""):
        # Print
        text = "Available tasks" if self.namespace is None else "Subcommands"
        if extra:
            text = "{} ({})".format(text, extra)
        print("{}:\n".format(text))
        self.print_columns(pairs)

    def list_flat(self, root):
        # TODO: honor root
        # TODO: honor depth
        # Sort in depth, then alpha, order
        task_names = self.collection.task_names
        pairs = []
        for primary in sort_names(task_names):
            # Add aliases
            aliases = sort_names(task_names[primary])
            name = primary
            if aliases:
                name += " ({})".format(', '.join(aliases))
            # Add docstring 1st lines
            task = self.collection[primary]
            pairs.append((name, helpline(task)))
        self.display_with_columns(pairs)

    def _nested_pairs(self, coll, level):
        # TODO: this still feels like it could follow the Collection.task_names
        # approach used by the default/flat style? But this data set is that
        # much farther removed from anything one would truly want from
        # Collection itself, in a vacuum. Implies we want to move that AND this
        # into some sort of Lister class hierarchy or set of funcs...bah.
        pairs = []
        indent = level * self.indent
        for name, task in sorted(six.iteritems(coll.tasks)):
            displayname = name
            aliases = list(map(coll.transform, task.aliases))
            if level > 0:
                displayname = ".{}".format(displayname)
                aliases = [".{}".format(x) for x in aliases]
            if coll.default == name:
                displayname += "*"
            alias_str = " ({})".format(", ".join(aliases)) if aliases else ""
            full = indent + displayname + alias_str
            pairs.append((full, helpline(task)))
        for name, subcoll in sorted(six.iteritems(coll.collections)):
            displayname = name
            if level > 0:
                displayname = ".{}".format(displayname)
            pairs.append((indent + displayname, helpline(subcoll)))
            pairs.extend(self._nested_pairs(subcoll, level + 1))
        return pairs

    def list_nested(self, root):
        # TODO: honor root
        # TODO: honor depth
        collection = self.collection
        pairs = self._nested_pairs(collection, level=0)
        extra = "'*' denotes collection defaults"
        self.display_with_columns(pairs, extra=extra)

    def print_columns(self, tuples):
        """
        Print tabbed columns from (name, help) ``tuples``.

        Useful for listing tasks + docstrings, flags + help strings, etc.
        """
        # Calculate column sizes: don't wrap flag specs, give what's left over
        # to the descriptions.
        name_width = max(len(x[0]) for x in tuples)
        desc_width = (
            pty_size()[0]
            - name_width
            - self.leading_indent_width
            - self.col_padding
            - 1
        )
        wrapper = textwrap.TextWrapper(width=desc_width)
        for name, help_str in tuples:
            # Wrap descriptions/help text
            help_chunks = wrapper.wrap(help_str)
            # Print flag spec + padding
            name_padding = name_width - len(name)
            spec = ''.join((
                self.leading_indent,
                name,
                name_padding * ' ',
                self.col_padding * ' '
            ))
            # Print help text as needed
            if help_chunks:
                print(spec + help_chunks[0])
                for chunk in help_chunks[1:]:
                    print((' ' * len(spec)) + chunk)
            else:
                print(spec.rstrip())
        print('')
