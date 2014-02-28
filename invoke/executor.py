from .util import debug


class Executor(object):
    """
    An execution strategy for Task objects.

    Subclasses may override various extension points to change, add or remove
    behavior.
    """
    def __init__(self, collection, context):
        """
        Initialize executor with handles to a task collection & config context.

        The collection is used for looking up tasks by name and
        storing/retrieving state, e.g. how many times a given task has been run
        this session and so on.

        A copy of the context is passed into any tasks that mark themselves as
        requiring one for operation.
        """
        self.collection = collection
        self.context = context

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
        all_tasks = self.task_list(task)
        debug("Task list, including pre/post tasks: %r" % (all_tasks,))
        # Dedupe if requested
        if dedupe:
            debug("Deduplication is enabled")
            # Compact (preserving order, so not using list+set)
            compact_tasks = []
            for task in all_tasks:
                if task not in compact_tasks:
                    compact_tasks.append(task)
            debug("Task list, obvious dupes removed: %r" % (compact_tasks,))
            # Remove tasks already called
            tasks = []
            for task in compact_tasks:
                if not task.called:
                    tasks.append(task)
            debug("Task list, already-called tasks removed: %r" % (tasks,))
        else:
            debug("Deduplication is DISABLED, above task list will run")
            tasks = all_tasks
        # Execute
        results = {}
        for t in tasks:
            debug("Executing %r" % t)
            args = []
            if t.contextualized:
                context = self.context.clone()
                path = '.'.join(name.split('.')[:-1])
                context.update(self.collection.configuration(path))
                args.append(context)
            results[t] = t(*args, **kwargs)
        return results[task]

    def task_list(self, task):
        tasks = [task]
        prereqs = []
        for pretask in task.pre:
            prereqs.append(self.collection[pretask])
        return prereqs + tasks
