import itertools

from .config import Config
from .context import Context
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

    def execute(self, *tasks, **kwargs):
        """
        Execute one or more ``tasks`` in sequence.

        :param tasks:
            An iterable of two-tuples whose first element is a task name and
            whose second element is a dict suitable for use as ``**kwargs``.
            E.g.::

                [
                    ('task1', {}),
                    ('task2', {'arg1': 'val1'}),
                    ...
                ]

            As a shorthand, a string instead of a two-tuple may be given,
            implying an empty kwargs dict.

            The string specifies which task from the Executor's `.Collection`
            is to be executed. It may contain dotted syntax appropriate for
            calling namespaced tasks, e.g. ``subcollection.taskname``.

            Thus the above list-of-tuples is roughly equivalent to::

                task1()
                task2(arg1='val1')

        :returns:
            A dict mapping task objects to their return values. This may
            include pre- and post-tasks if any were executed.
        """
        # Handle top level kwargs (the name gets overwritten below)
        # Normalize input
        debug("Examining top level tasks {0!r}".format([x[0] for x in tasks]))
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
        # To two-tuples from potential combo of two-tuples & strings
        tuples = [
            (x, {}) if isinstance(x, six.string_types) else x
            for x in tasks
        ]
        # Then to call objects (binding the task obj + kwargs together)
        calls = []
        for name, kwargs in tuples:
            c = Call(self.collection[name], **kwargs)
            c.name = name
            calls.append(c)
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
        debug("Executing %r%s" % (task, (" as %s" % name) if name else ""))
        if task.contextualized:
            config.load_collection(self.collection.configuration(name))
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
