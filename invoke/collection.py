from lexicon import Lexicon

from .parser import Context, Argument


class Collection(object):
    def __init__(self, *tasks):
        self.tasks = Lexicon()
        self.default = None
        for task in tasks:
            self.add_task(task)

    def add_task(self, task, name=None, aliases=(), default=False):
        """
        Adds callable object ``task`` to this collection.

        If ``name`` is not explicitly given (recommended) the ``.func_name`` of
        the given callable will be used instead.

        If ``aliases`` is given, will be used to set up additional aliases for
        this task.

        ``default`` may be set to ``True`` to set the task as this collection's
        default invocation.
        """
        if name is None:
            if hasattr(task.body, 'func_name'):
                name = task.body.func_name
            else:
                raise ValueError("'name' may only be empty if 'task' wraps an object exposing .func_name")
        self.tasks[name] = task
        for alias in aliases:
            self.tasks.alias(alias, to=name)
        if default:
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def __getitem__(self, name=None):
        """
        Returns task named ``name``. Honors aliases.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.
        """
        if not name:
            if self.default:
                return self[self.default]
            else:
                raise ValueError("This collection has no default task.")
        return self.tasks[name]

    def __contains__(self, name):
        return name in self.tasks

    def to_contexts(self):
        """
        Returns all contained tasks and subtasks as a list of parser contexts.
        """
        result = []
        for name, task in self.tasks.iteritems():
            context = Context(name=name, aliases=task.aliases)
            argspec = task.argspec
            for name, default in argspec.iteritems():
                # Handle arg options
                opts = {}
                opts['help'] = task.helps.get(name)
                if default is not None:
                    opts['kind'] = type(default)
                # Handle aliases (auto shortflags, etc)
                names = [name]
                names.extend(argspec.aliases_of(name))
                # Create/add the argument
                context.add_arg(names=names, **opts)
            result.append(context)
        return result
