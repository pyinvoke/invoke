import itertools

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
    def __init__(self, collection, context=None):
        """
        Initialize executor with handles to a task collection & config context.

        The collection is used for looking up tasks by name and
        storing/retrieving state, e.g. how many times a given task has been
        run this session and so on. It is optional; if not given a blank
        `.Context` is used.

        A copy of the context is passed into any tasks that mark themselves as
        requiring one for operation.
        """
        self.collection = collection
        self.context = context or Context()

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

        :param bool dedupe:
            Whether to perform deduplication on the tasks and their
            pre/post-tasks. See :ref:`deduping`.

        :returns:
            A dict mapping task objects to their return values. This may
            include pre- and post-tasks if any were executed.
        """
        # Handle top level kwargs (the name gets overwritten below)
        dedupe = kwargs.get('dedupe', True) # Python 2 can't do *args + kwarg
        # Normalize input
        debug("Examining top level tasks {0!r}".format([x[0] for x in tasks]))
        tasks = self._normalize(tasks)
        debug("Tasks with kwargs: {0!r}".format(tasks))
        # Obtain copy of directly-given tasks since they should sometimes
        # behave differently
        direct = list(tasks)
        # Expand pre/post tasks & then dedupe the entire run
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
                task=task, name=name, args=args, kwargs=kwargs
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
            for task in tasks:
                if task not in deduped:
                    deduped.append(task)
        else:
            deduped = tasks
        return deduped

    def _execute(self, task, name, args, kwargs):
        # Need task + possible name when invoking CLI-given tasks, so we can
        # pass a dotted path to Collection.configuration()
        debug("Executing %r%s" % (task, (" as %s" % name) if name else ""))
        if task.contextualized:
            context = self.context.clone()
            # TODO: this needs to be different because this collection based
            # config needs to be *below* all the other values in the
            # context/config object.
            # But can it still just be a single method call in this location?
            # Probably becomes: add Defaults to copy of base config, + calls
            # Config.load() to perform actual loading. (This may mean
            # loading conf files multiple times? eh)
            context.update(self.collection.configuration(name))
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
