class Collection(object):
    def __init__(self):
        self.tasks = {}
        self.aliases = {}

    def add_task(self, name, task, aliases=(), default=False):
        """
        Adds callable object ``task`` to this collection under name ``name``.

        If ``aliases`` is given, will be used to set up additional aliases for
        this task. ``default`` may be set to ``True`` to set the task as this
        collection's default invocation.
        """
        self.tasks[name] = task

    def get(self, name):
        return self.tasks[name]
