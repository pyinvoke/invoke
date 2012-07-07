from lexicon import Lexicon

from .parser import Context, Argument


class Collection(object):
    def __init__(self):
        self.tasks = Lexicon()
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
            self.tasks.alias(alias, to=name)
        if default:
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def get(self, name=None):
        """
        Returns task named ``name``. Honors aliases.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.
        """
        if not name:
            if self.default:
                return self.get(self.default)
            else:
                raise ValueError("This collection has no default task.")
        return self.tasks[name]

    def to_contexts(self):
        """
        Returns all contained tasks and subtasks as a list of parser contexts.
        """
        result = []
        for name, task in self.tasks.iteritems():
            context = Context(name=name, aliases=task.aliases)
            argspec = task.argspec
            for name, default in argspec.iteritems():
                opts = {}
                if default is not None:
                    opts['kind'] = type(default)
                names = [name]
                # Handle auto short flags
                for char in name:
                    if not (
                        char in context.args
                        or char in names
                        or char in argspec
                    ):
                        names.append(char)
                        break
                context.add_arg(names=names, **opts)
            result.append(context)
        return result
