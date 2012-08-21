import inspect

from lexicon import Lexicon


class Task(object):
    # TODO: store these kwarg defaults central, refer to those values both here
    # and in @task
    def __init__(self, body, aliases=(), default=False, auto_shortflags=True,
        helps={}):
        self.body = body
        self.aliases = aliases
        self.is_default = default
        self.auto_shortflags = auto_shortflags
        self.helps = helps

    @property
    def argspec(self):
        """
        Introspect wrapped function for arg names, default values etc.
        """
        spec = inspect.getargspec(self.body)
        # Associate default values with their respective arg names
        if spec.defaults is not None:
            ret = Lexicon(zip(spec.args[-len(spec.defaults):], spec.defaults))
        else:
            ret = Lexicon()
        # Pull in args that have no default values
        ret.update((x, None) for x in spec.args if x not in ret)
        # Handle auto short flags
        if self.auto_shortflags:
            for name in ret:
                alias = None
                for char in name:
                    if not (char == name or char in ret):
                        alias = char
                        break
                if alias:
                    ret.alias(alias, to=name)
        return ret


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
    * ``default``: Boolean option specifying whether this task should be its
      collection's default task (i.e. called if the collection's own name is
      given.)
    * ``auto_shortflags``: Whether or not to :ref:`automatically create short
      flags <automatic-shortflags>` from task options; defaults to True.
    * ``help``: Dict mapping argument names to their help strings. Will be
      displayed in ``--help`` output.
    """
    # @task -- no options
    if len(args) == 1:
        obj = args[0]
        obj = Task(obj)
        return obj
    # @task(options)
    aliases = kwargs.pop('aliases', ())
    default = kwargs.pop('default', False)
    auto_shortflags = kwargs.pop('auto_shortflags', True)
    helps = kwargs.pop('help', {})
    # Handle unknown args/kwargs
    if args or kwargs:
        arg = (" unknown args %r" % (args,)) if args else ""
        kwarg = (" unknown kwargs %r" % (kwargs,)) if kwargs else ""
        raise TypeError("@task was called with" + arg + kwarg)
    def inner(obj):
        obj = Task(
            obj,
            aliases=aliases,
            default=default,
            auto_shortflags=auto_shortflags,
            helps=helps,
        )
        return obj
    return inner
