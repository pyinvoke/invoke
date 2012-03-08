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
        for alias in aliases:
            self.add_alias(from_=alias, to=name)

    def add_alias(self, from_, to):
        """
        Add an alias from ``from_`` to ``to``.

        Aliases may be recursive, i.e. ``to`` may itself point to an alias
        name.
        """
        self.aliases[from_] = to

    def get(self, name):
        """
        Returns task named ``name``.

        Honors aliases. In the event that a task has a non-alias name ``X``
        **and** some task has an alias ``X``, the "real" non-aliased task will
        win.
        """
        while name not in self.tasks:
            try:
                name = self.aliases[name]
            except KeyError:
                break
        return self.tasks[name]
