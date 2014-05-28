import itertools

from .context import Context
from .util import debug
from .tasks import Call

from .vendor import six


def expand_tasks(tasks):
    ret = []
    for task in tasks:
        ret.extend(expand_tasks(task.pre))
        ret.append(task)
        # TODO: ret.extend(expand_tasks(tasks.post))
    return ret

def normalize_tuples(tuples):
    return [(x, {}) if isinstance(x, basestring) else x for x in tuples]


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
        `~invoke.context.Context` is used.

        A copy of the context is passed into any tasks that mark themselves as
        requiring one for operation.
        """
        self.collection = collection
        self.context = context or Context()

    def _execute(self, task, name, args, kwargs):
        # Need task + possible name when invoking CLI-given tasks, so we can
        # pass a dotted path to Collection.configuration()
        debug("Executing %r%s" % (task, (" as %s" % name) if name else ""))
        if task.contextualized:
            context = self.context.clone()
            context.update(self.collection.configuration(name))
            args = (context,) + args
        return task(*args, **kwargs)

    def execute(self, *tasks, **kwargs):
        """
        Execute one or more ``tasks`` in sequence.

        :param iterable tasks:
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
            pre/post-tasks.

        :returns:
            A list of the return values from the tasks invoked, in the order
            they were given. Pre- and post-tasks' return values are discarded.
        """
        dedupe = kwargs.get('dedupe', True) # Python 2 can't do *args + kwarg
        results = []
        for name, kwargs in normalize_tuples(tasks):
            # Expand task list
            task = self.collection[name]
            debug("Executor is examining top level task %r (name given: %r)" % (
                task, name
            ))
            # TODO: post-tasks
            debug("Pre-tasks, immediate: {0}".format(task.pre))
            pre = list(expand_tasks(task.pre))
            debug("Pre-tasks, expanded: {0}".format(pre))
            # Dedupe if requested
            if dedupe:
                debug("Deduplication is enabled")
                # Compact (preserving order, so not using list+set)
                compact_pre = []
                for t in pre:
                    if t not in compact_pre:
                        compact_pre.append(t)
                pre = compact_pre
                debug("Pre-tasks, dupes removed: %r" % (pre,))
            else:
                debug("Deduplication is DISABLED, above pre-task list will run")
            # Execute
            for t in pre:
                # TODO: intelligent result capture
                # Execute task w/o a given name since it's a pre-task.
                # TODO: figure out if that's quite right (may not play well with
                # nested config junk)
                pre_args, pre_kwargs = tuple(), {}
                if isinstance(t, Call):
                    c = t
                    t = c.task
                    pre_args, pre_kwargs = c.args, c.kwargs
                self._execute(task=t, name=None, args=pre_args, kwargs=pre_kwargs)
            result = self._execute(task=task, name=name, args=tuple(), kwargs=kwargs)
            results.append(result)
        return results
