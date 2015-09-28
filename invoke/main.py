"""
Invoke's own 'binary' entrypoint.

Dogfoods the `program` module.
"""

from . import __version__, Program, Argument
from .util import debug, enable_logging, sort_names
from .exceptions import Failure, CollectionNotFound, ParseError, Exit
from .complete import complete

class InvokeProgram(Program):
    def core_args(self):
        """
        In the ``invoke`` cli tool, extend the arguments list to
        include those core arguments that are ``invoke`` specific.
        """
        self.task_args = [
            Argument(
                names=('collection', 'c'),
                help="Specify collection name to load."
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
                names=('root', 'r'),
                help="Change root directory used for finding task modules."
            ),
        ]
        args = super(InvokeProgram, self).core_args()
        args.extend(self.task_args)
        return args

    def handle_args(self):
        self.search_start_info = self.args.root.value
        self.search_collection_name = self.args.collection.value

    def setup_tasks(self):
        super(InvokeProgram, self).handle_args()
        # Print discovered tasks if necessary
        if self.args.list.value:
            self.list_tasks()
            raise Exit

        # Print completion helpers if necessary
        if self.args.complete.value:
            complete(self.core, self.initial_context, self.collection)

        # No tasks specified for execution & no default task = print help
        # NOTE: when there is a default task, Executor will select it when no
        # tasks were found in CLI parsing.
        if not self.tasks and not self.collection.default:
            debug("No tasks specified for execution and no default task; printing global help as fallback") # noqa
            self.print_help()
            raise Exit

    def print_help(self):
        super(InvokeProgram, self).print_help()
        if hasattr(self, 'collection'):
            debug("print help is aware of collection adding task list for: {}".format(self.collection))
            self.list_tasks()

    def list_tasks(self):
        # Sort in depth, then alpha, order
        task_names = self.collection.task_names
        # Short circuit if no tasks to show
        if not task_names:
            msg = "No tasks found in collection '{0}'!"
            print(msg.format(self.collection.name))
            raise Exit
        pairs = []
        for primary in sort_names(task_names):
            # Add aliases
            aliases = sort_names(task_names[primary])
            name = primary
            if aliases:
                name += " ({0})".format(', '.join(aliases))
            # Add docstring 1st lines
            task = self.collection[primary]
            help_ = ""
            if task.__doc__:
                help_ = task.__doc__.lstrip().splitlines()[0]
            pairs.append((name, help_))

        # Print
        if self.namespace is not None:
            print("Subcommands:\n")
        else:
            print("Available tasks:\n")
        self.print_columns(pairs)

program = InvokeProgram(
    name="Invoke",
    binary='inv[oke]',
    version=__version__,
)
