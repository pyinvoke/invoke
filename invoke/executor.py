from .config import Config
from .context import Context
from .parser import ParserContext
from .util import debug
from .tasks import Call

from .vendor import six


class Executor(object):
    """
    An execution strategy for Task objects.

    Subclasses may override various extension points to change, add or remove
    behavior.
    """
    def __init__(self, collection, config=None):
        """
        Initialize executor with handles to a task collection & config.

        :param collection:
            A `.Collection` used to look up requested tasks (and their default
            config data, if any) by name during execution.

        :param config:
            An optional `.Config` holding configuration state Defaults to an
            empty `.Config` if not given.
        """
        self.collection = collection
        if config is None:
            config = Config()
        self.config = config

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
            as the task name and whose ``.as_kawrgs`` attribute is used as the
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
        # Handle top level kwargs (the name gets overwritten below)
        # Normalize input
        debug("Examining top level tasks {0!r}".format([x for x in tasks]))
        tasks = self._normalize(tasks)
        debug("Tasks with kwargs: {0!r}".format(tasks))
        # Obtain copy of directly-given tasks since they should sometimes
        # behave differently
        direct = list(tasks)
        # Expand pre/post tasks & then dedupe the entire run.
        # Load config at this point to get latest value of dedupe option
        config = self.config.clone()
        # Get some good value for dedupe option, even if config doesn't have
        # the tree we expect. (This is a concession to testing.)
        try:
            dedupe = config.tasks.dedupe
        except AttributeError:
            dedupe = True
        # Actual deduping here
        tasks = self._dedupe(self._expand_tasks(tasks), dedupe)
        # Execute
        results = {}
        for task in tasks:
            args, kwargs = tuple(), {}
            # Unpack Call objects, including given-name handling
            name = None
            autoprint = task in direct and task.autoprint
            if isinstance(task, Call):
                c = task
                task = c.task
                args, kwargs = c.args, c.kwargs
                name = c.name
            result = self._execute(
                task=task, name=name, args=args, kwargs=kwargs, config=config
            )
            if autoprint:
                print(result)
            # TODO: handle the non-dedupe case / the same-task-different-args
            # case, wherein one task obj maps to >1 result.
            results[task] = result
        return results

    def _normalize(self, tasks):
        """
        Transform arbitrary task list w/ various types, into `.Call` objects.

        See docstring for `.execute` for details.
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
            c = Call(self.collection[name], **kwargs)
            c.name = name
            calls.append(c)
        if not tasks and self.collection.default is not None:
            calls = [Call(self.collection[self.collection.default])]
        return calls

    def _dedupe(self, tasks, dedupe):
        deduped = []
        if dedupe:
            debug("Deduplicating tasks...")
            for task in tasks:
                if task not in deduped:
                    debug("{0!r}: ok".format(task))
                    deduped.append(task)
                else:
                    debug("{0!r}: skipping".format(task))
        else:
            deduped = tasks
        return deduped

    def _execute(self, task, name, args, kwargs, config):
        # Need task + possible name when invoking CLI-given tasks, so we can
        # pass a dotted path to Collection.configuration()
        debug("Executing {0!r}{1}".format(
            task,
            (" as {0}".format(name)) if name else ""),
        )
        if task.contextualized:
            # Load per-task/collection config
            config.load_collection(self.collection.configuration(name))
            # Load env vars, as the last step (so users can override
            # per-collection keys via the env)
            config.load_shell_env()
            # Set up context w/ that config
            context = Context(config=config)
            args = (context,) + args
        result = task(*args, **kwargs)
        return result

    def _expand_tasks(self, tasks):
        ret = []
        for task in tasks:
            ret.extend(self._expand_tasks(task.pre))
            ret.append(task)
            ret.extend(self._expand_tasks(task.post))
        return ret
