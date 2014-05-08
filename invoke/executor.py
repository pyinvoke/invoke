from .context import Context
from .util import debug


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

    def execute(self, name, kwargs=None, dedupe=True):
        """
        Execute a named task, honoring pre- or post-tasks and so forth.

        :param name:
            A string naming which task from the Executor's `.Collection` is to
            be executed. May contain dotted syntax appropriate for calling
            namespaced tasks, e.g. ``subcollection.taskname``.

        :param kwargs:
            A keyword argument dict expanded when calling the requested task.
            E.g.::

                executor.execute('mytask', {'myarg': 'foo'})

            is (roughly) equivalent to::

                mytask(myarg='foo')

        :param dedupe:
            Ensures any given task within ``self.collection`` is only run once
            per session. Set to ``False`` to disable this behavior.

        :returns:
            The return value of the named task -- regardless of whether pre- or
            post-tasks are executed.
        """
        kwargs = kwargs or {}
        # Expand task list
        task = self.collection[name]
        debug("Executor is examining top level task %r" % task)
        # TODO: post-tasks
        pre = list(task.pre)
        debug("Pre-tasks: %r" % (pre,))
        # Dedupe if requested
        if dedupe:
            debug("Deduplication is enabled")
            # Compact (preserving order, so not using list+set)
            compact_pre = []
            for tname in pre:
                if tname not in compact_pre:
                    compact_pre.append(tname)
            debug("Pre-tasks, obvious dupes removed: %r" % (compact_pre,))
            # Remove tasks already called
            pre = []
            for tname in compact_pre:
                if not self.collection[tname].called:
                    pre.append(tname)
            debug("Pre-tasks, already-called tasks removed: %r" % (pre,))
        else:
            debug("Deduplication is DISABLED, above pre-task list will run")
        # Execute
        results = {}
        for tname in pre + [name]:
            t = self.collection[tname]
            debug("Executing %r" % t)
            args = []
            if t.contextualized:
                context = self.context.clone()
                context.update(self.collection.configuration(tname))
                args.append(context)
            results[t] = t(*args, **kwargs)
        return results[task]
