from .config import Config
from .context import Context
from .parser import ParserContext
from .util import debug
from .tasks import Call, Task

from .vendor import six


class Executor(object):
    """
    An execution strategy for Task objects.

    Subclasses may override various extension points to change, add or remove
    behavior.
    """
    def __init__(self, collection, config=None, core=None):
        """
        Initialize executor with handles to necessary data structures.

        :param collection:
            A `.Collection` used to look up requested tasks (and their default
            config data, if any) by name during execution.

        :param config:
            An optional `.Config` holding configuration state Defaults to an
            empty `.Config` if not given.

        :param core:
            An optional `.ParserContext` holding core program arguments.
            Defaults to ``None``.

            .. note::
                This is unused by the default implementation, but may be useful
                to subclasses which care about specific core arguments re:
                execution strategy, use of the parse remainder, etc.
        """
        self.collection = collection
        self.config = config if config is not None else Config()
        self.core = core

    def execute(self, *tasks):
        """
        Execute one or more ``tasks`` in sequence.

        :param tasks:
            An all-purpose iterable of "tasks to execute", each member of which
            may take one of the following forms:

            **A string** naming a task from the Executor's `.Collection`. This
            name may contain dotted syntax appropriate for calling namespaced
            tasks, e.g. ``subcollection.taskname``. Such tasks are executed
            without arguments.

            **A two-tuple** whose first element is a task name string (as
            above) and whose second element is a dict suitable for use as
            ``**kwargs`` when calling the named task. E.g.::

                [
                    ('task1', {}),
                    ('task2', {'arg1': 'val1'}),
                    ...
                ]

            is equivalent, roughly, to::

                task1()
                task2(arg1='val1')

            **A `.ParserContext`** instance, whose ``.name`` attribute is used
            as the task name and whose ``.as_kwargs`` attribute is used as the
            task kwargs (again following the above specifications).

            .. note::
                When called without any arguments at all (i.e. when ``*tasks``
                is empty), the default task from ``self.collection`` is used
                instead, if defined.

        :returns:
            A dict mapping task objects to their return values.

            This dict may include pre- and post-tasks if any were executed. For
            example, in a collection with a ``build`` task depending on another
            task named ``setup``, executing ``build`` will result in a dict
            with two keys, one for ``build`` and one for ``setup``.
        """
        # Normalize input
        debug("Examining top level tasks {0!r}".format([x for x in tasks]))
        calls = self.normalize(tasks)
        debug("Tasks (now Calls) with kwargs: {0!r}".format(calls))
        # Obtain copy of directly-given tasks since they should sometimes
        # behave differently
        direct = list(calls)
        # Expand pre/post tasks & then dedupe the entire run.
        # Load config at this point to get latest value of dedupe option
        config = self.config.clone()
        expanded = self.expand_calls(calls, config)
        # Get some good value for dedupe option, even if config doesn't have
        # the tree we expect. (This is a concession to testing.)
        try:
            dedupe = config.tasks.dedupe
        except AttributeError:
            dedupe = True
        # Actual deduping here
        calls = self.dedupe(expanded) if dedupe else expanded
        # Execute
        results = {}
        for call in calls:
            autoprint = call in direct and call.autoprint
            args = call.args
            debug("Executing {0!r}".format(call))
            args = (call.context,) + args
            result = call.task(*args, **call.kwargs)
            if autoprint:
                print(result)
            # TODO: handle the non-dedupe case / the same-task-different-args
            # case, wherein one task obj maps to >1 result.
            results[call.task] = result
        return results

    def normalize(self, tasks):
        """
        Transform arbitrary task list w/ various types, into `.Call` objects.

        See docstring for `~.Executor.execute` for details.
        """
        calls = []
        for task in tasks:
            name, kwargs = None, {}
            if isinstance(task, six.string_types):
                name = task
            elif isinstance(task, ParserContext):
                name = task.name
                kwargs = task.as_kwargs
            else:
                name, kwargs = task
            c = Call(task=self.collection[name], kwargs=kwargs, called_as=name)
            calls.append(c)
        if not tasks and self.collection.default is not None:
            calls = [Call(task=self.collection[self.collection.default])]
        return calls

    def dedupe(self, calls):
        """
        Deduplicate a list of `tasks <.Call>`.

        :param calls: An iterable of `.Call` objects representing tasks.

        :returns: A list of `.Call` objects.
        """
        deduped = []
        debug("Deduplicating tasks...")
        for call in calls:
            if call not in deduped:
                debug("{0!r}: no duplicates found, ok".format(call))
                deduped.append(call)
            else:
                debug("{0!r}: found in list already, skipping".format(call))
        return deduped

    def expand_calls(self, calls, config):
        """
        Expand a list of `.Call` objects into a near-final list of same.

        The default implementation of this method simply adds a task's
        pre/post-task list before/after the task itself, as necessary.

        Subclasses may wish to do other things in addition (or instead of) the
        above, such as multiplying the `calls <.Call>` by argument vectors or
        similar.
        """
        ret = []
        for call in calls:
            # Normalize to Call (this method is sometimes called with pre/post
            # task lists, which may contain 'raw' Task objects)
            if isinstance(call, Task):
                call = Call(task=call)
            debug("Expanding task-call {0!r}".format(call))
            call.context = Context(config=self.config_for(call, config))
            # NOTE: handing in original config, not the mutated one handed to
            # the Context above. Pre/post tasks may well come from a different
            # collection, etc. Also just cleaner.
            ret.extend(self.expand_calls(call.pre, config))
            ret.append(call)
            ret.extend(self.expand_calls(call.post, config))
        return ret

    def config_for(self, call, config, anonymous=False):
        """
        Generate a `.Config` object suitable for the given task call.

        :param call: `.Call` object to create config for.

        :param config: Core `.Config` object to clone & build upon.

        :param bool anonymous:
            If ``True``, treat task as anonymous and don't try loading
            collection-based config for it. (Useful for downstream code which
            may be adding dynamically-created, collection-less tasks during the
            load process.)
        """
        task_config = config.clone()
        if not anonymous:
            # Load collection-local config
            task_config.load_collection(
                self.collection.configuration(call.called_as)
            )
        # Load env vars, as the last step (so users can override
        # per-collection keys via the env)
        task_config.load_shell_env()
        debug("Finished loading collection & shell env configs")
        # Set up context w/ that config & add to call obj
        # TODO: fab needs to override the class here & some of its
        # kwargs, based on values that it derives from core args & the
        # task
        return task_config
