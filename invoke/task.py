import inspect
from itertools import izip_longest

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

    def arg_opts(self, name, default, taken_names):
        # Argument name(s)
        names = [name]
        if self.auto_shortflags and name not in self.positional:
            # Must know what short names are available
            for char in name:
                if not (char == name or char in taken_names):
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
        # Get argspec in dict format for easy name=>default lookup during list
        # construction
        spec = inspect.getargspec(self.body)
        arg_names = spec.args[:]
        matched_args = [reversed(x) for x in [spec.args, spec.defaults or []]]
        spec_dict = dict(izip_longest(*matched_args, fillvalue=None))
        # Obtain ordered list of args + their default values (if any).
        # Order should be: positionals, in order given in decorator, followed
        # by non-positionals, in order declared (i.e. exposed by
        # getargspect()).
        tuples = []
        # Positionals first, removing from base list of arg names
        for posarg in self.positional:
            tuples.append((posarg, spec_dict[posarg]))
            arg_names.remove(posarg)
        # Now arg_names contains just the non-positional args, in order.
        tuples.extend((x, spec_dict[x]) for x in arg_names)
        # Prime the list of all already-taken names (mostly for help in
        # choosing auto shortflags)
        taken_names = set(x[0] for x in tuples)
        # Build + return arg list
        args = []
        for name, default in tuples:
            new_arg = Argument(**self.arg_opts(name, default, taken_names))
            args.append(new_arg)
            # Update taken_names list with new argument's full name list
            # (which may include new shortflags)
            taken_names.update(set(new_arg.names))
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
