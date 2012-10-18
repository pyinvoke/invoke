import inspect

from lexicon import Lexicon

from .parser import Argument


class Task(object):
    # TODO: store these kwarg defaults central, refer to those values both here
    # and in @task
    def __init__(self, body, aliases=(), positional=(), default=False, 
        auto_shortflags=True):
        self.body = body
        self.aliases = aliases
        self.positional = positional
        self.is_default = default
        self.auto_shortflags = auto_shortflags

    def arg_opts(self, name, default, others):
        # Argument name(s)
        names = [name]
        if self.auto_shortflags and name not in self.positional:
            # Must know what short names are available
            taken = reduce(lambda x, y: x + list(y.names), others, [])
            for char in name:
                if not (char == name or char in taken):
                    names.append(char)
                    break
        opts = {'names': names}
        # Handle default value & kind
        if default is not None:
            # TODO: allow setting 'kind' explicitly.
            opts['kind'] = type(default)
            opts['default'] = default
        opts['positional'] = name in self.positional
        return opts

    def get_arguments(self):
        """
        Return a list of Argument objects representing this task's signature.
        """
        # TODO: there are 2 shitty methods of handling data structures in this
        # method. Can you spot & fix both of them?
        spec = inspect.getargspec(self.body)
        args = []
        # Associate default values with their respective arg names
        defaults = {}
        if spec.defaults is not None:
            defaults.update(zip(spec.args[-len(spec.defaults):], spec.defaults))
        # Pull in args that have no default values
        defaults.update((x, None) for x in spec.args if x not in defaults)
        # Build Argument objects (positionals first so they're added in order
        # by anybody consuming our result set.)
        for name in self.positional:
            default = defaults.pop(name)
            args.append(Argument(**self.arg_opts(name, default, args)))
        for name, default in defaults.iteritems():
            if name in self.positional:
                continue
            args.append(Argument(**self.arg_opts(name, default, args)))
        return args


def task(*args, **kwargs):
    """
    Marks wrapped callable object as a valid Invoke task.

    May be called without any parentheses if no extra options need to be
    specified. Otherwise, the following options are allowed in the parenthese'd
    form:

    * ``aliases``: Specify one or more aliases for this task, allowing it to be
      invoked as multiple different names. For example, a task named ``mytask``
      with a simple ``@task`` wrapper may only be invoked as ``"mytask"``.
      Changing the decorator to be ``@task(aliases=['myothertask'])`` allows
      invocation as ``"mytask"`` *or* ``"myothertask"``.
    * ``positional``: Iterable informing the parser that the given argument
      name(s) are to be treated as positional arugments and not flags.
    * ``default``: Boolean option specifying whether this task should be its
      collection's default task (i.e. called if the collection's own name is
      given.)
    * ``auto_shortflags``: Whether or not to :ref:`automatically create short
      flags <automatic-shortflags>` from task options; defaults to True.
    """
    # @task -- no options
    if len(args) == 1:
        obj = args[0]
        obj = Task(obj)
        return obj
    # @task(options)
    # TODO: pull in centrally defined defaults here (see Task)
    aliases = kwargs.pop('aliases', ())
    positional = kwargs.pop('positional', ())
    default = kwargs.pop('default', False)
    auto_shortflags = kwargs.pop('auto_shortflags', True)
    # Handle unknown args/kwargs
    if args or kwargs:
        arg = (" unknown args %r" % (args,)) if args else ""
        kwarg = (" unknown kwargs %r" % (kwargs,)) if kwargs else ""
        raise TypeError("@task was called with" + arg + kwarg)
    def inner(obj):
        obj = Task(
            obj,
            aliases=aliases,
            positional=positional,
            default=default,
            auto_shortflags=auto_shortflags
        )
        return obj
    return inner
