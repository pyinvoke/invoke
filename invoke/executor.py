from .context import Context
from .util import debug
from .tasks import Call


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
        # Expand task list
        task = self.collection[name]
        debug("Executor is examining top level task %r (name given: %r)" % (
            task, name
        ))
        # TODO: post-tasks
        # TODO: recursion
        pre = list(task.pre)
        debug("Pre-tasks: %r" % (pre,))
        # Dedupe if requested
        if dedupe:
            debug("Deduplication is enabled")
            # Compact (preserving order, so not using list+set)
            compact_pre = []
            for t in pre:
                if t not in compact_pre:
                    compact_pre.append(t)
            debug("Pre-tasks, obvious dupes removed: %r" % (compact_pre,))
            # Remove tasks already called
            pre = []
            for t in compact_pre:
                if not t.called:
                    pre.append(t)
            debug("Pre-tasks, already-called tasks removed: %r" % (pre,))
        else:
            debug("Deduplication is DISABLED, above pre-task list will run")
        # Execute
        results = {}
        kwargs = kwargs or {}
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
        return self._execute(task=task, name=name, args=tuple(), kwargs=kwargs)
