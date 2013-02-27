class Executor(object):
    """
    An execution strategy for Task objects.

    Subclasses may override various extension points to change, add or remove
    behavior.
    """
    def __init__(self, collection):
        """
        Create executor with a pointer to the task collection ``collection``.

        This pointer is used for looking up tasks by name and
        storing/retrieving state, e.g. how many times a given task has been run
        this session and so on.
        """
        self.collection = collection

    def execute(self, name, kwargs=None, dedupe=True):
        """
        Execute task named ``name``, optionally passing along ``kwargs``.

        If ``dedupe`` is ``True`` (default), will ensure any given task within
        ``self.collection`` is only run once per session. To disable this
        behavior, say ``dedupe=False``.
        """
        kwargs = kwargs or {}
        # Expand task list
        all_tasks = self.task_list(name)
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
        for task in tasks:
            task(**kwargs)

    def task_list(self, name):
        task = self.collection[name]
        tasks = [task]
        prereqs = []
        for pretask in task.pre:
            prereqs.append(self.collection[pretask])
        return prereqs + tasks
