class Collection(object):
    def __init__(self):
        self.tasks = {}
        self.aliases = {}
        self.default = None

    def add_task(self, name, task, aliases=(), default=False):
        """
        Adds callable object ``task`` to this collection under name ``name``.

        If ``aliases`` is given, will be used to set up additional aliases for
        this task.

        ``default`` may be set to ``True`` to set the task as this collection's
        default invocation.
        """
        self.tasks[name] = task
        for alias in aliases:
            self.add_alias(from_=alias, to=name)
        if default:
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def add_alias(self, from_, to):
        """
        Add an alias from ``from_`` to ``to``.

        Aliases may be recursive, i.e. ``to`` may itself point to an alias
        name.
        """
        self.aliases[from_] = to

    def get(self, name=None):
        """
        Returns task named ``name``.

        Honors aliases. In the event that a task has a non-alias name ``X``
        **and** some task has an alias ``X``, the "real" non-aliased task will
        win.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.
        """
        if not name:
            if self.default:
                return self.get(self.default)
            else:
                raise ValueError("This collection has no default task.")
        while name not in self.tasks:
            try:
                name = self.aliases[name]
            except KeyError:
                break
        return self.tasks[name]
