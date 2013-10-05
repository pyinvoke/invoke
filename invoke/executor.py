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
        all_tasks = self.task_list(task)
        # Dedupe if requested
        if dedupe:
            # Compact (preserving order, so not using list+set)
            compact_tasks = []
            for task in all_tasks:
                if task not in compact_tasks:
                    compact_tasks.append(task)
            # Remove tasks already called
            tasks = []
            for task in compact_tasks:
                if not task.called:
                    tasks.append(task)
        else:
            tasks = all_tasks
        # Execute
        results = {}
        for t in tasks:
            args = []
            if t.contextualized:
                context = self.context.clone()
                context.update(self.collection.configuration)
                args.append(context)
            results[t] = t(*args, **kwargs)
        return results[task]

    def task_list(self, task):
        tasks = [task]
        prereqs = []
        for pretask in task.pre:
            prereqs.append(self.collection[pretask])
        return prereqs + tasks
