import inspect
from itertools import izip_longest

from .vendor.lexicon import Lexicon

from .parser import Argument


# Non-None sentinel
NO_DEFAULT = object()


class Task(object):
    # TODO: store these kwarg defaults central, refer to those values both here
    # and in @task.
    # TODO: allow central per-session / per-taskmodule control over some of
    # them, e.g. (auto_)positional, auto_shortflags.
    def __init__(self, body, aliases=(), positional=None, default=False, 
        auto_shortflags=True):
        self.body = body
        self.aliases = aliases
        self.positional = self.fill_implicit_positionals(positional)
        self.is_default = default
        self.auto_shortflags = auto_shortflags

    def argspec(self, body):
        """
        Returns two-tuple:

        * First item is list of arg names, in order defined.
        * Second item is dict mapping arg names to default values or
          task.NO_DEFAULT (i.e. an 'empty' value distinct from None).
        """
        spec = inspect.getargspec(body)
        arg_names = spec.args[:]
        matched_args = [reversed(x) for x in [spec.args, spec.defaults or []]]
        spec_dict = dict(izip_longest(*matched_args, fillvalue=NO_DEFAULT))
        return arg_names, spec_dict

    def fill_implicit_positionals(self, positional):
        _, spec_dict = self.argspec(self.body)
        # If positionals is None, everything lacking a default
        # value will be automatically considered positional.
        if positional is None:
            positional = []
            for name, default in spec_dict.iteritems():
                if default is NO_DEFAULT:
                    positional.append(name)
        return positional

    def arg_opts(self, name, default, taken_names):
        # Argument name(s)
        names = [name]
        if self.auto_shortflags:
            # Must know what short names are available
            for char in name:
                if not (char == name or char in taken_names):
                    names.append(char)
                    break
        opts = {'names': names}
        # Handle default value & kind if possible
        if default not in (None, NO_DEFAULT):
            # TODO: allow setting 'kind' explicitly.
            opts['kind'] = type(default)
            opts['default'] = default
        opts['positional'] = name in self.positional
        return opts

    def get_arguments(self):
        """
        Return a list of Argument objects representing this task's signature.
        """
        arg_names, spec_dict = self.argspec(self.body)
        # Obtain ordered list of args + their default values (if any).
        # Order should be: positionals, in order given in decorator, followed
        # by non-positionals, in order declared (i.e. exposed by
        # getargspect()).
        tuples = []
        # Positionals first, removing from base list of arg names
        # FIXME: WHY are positionals first?
        # It messes up expected shortflags order now that positionals are flags
        # again!
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
    * ``positional``: Iterable overriding the parser's automatic "args with no
      default value are considered positional" behavior. If a list of arg
      names, no args besides those named in this iterable will be considered
      positional. (This means that an empty list will force all arguments to be
      given as explicit flags.)
    * ``default``: Boolean option specifying whether this task should be its
      collection's default task (i.e. called if the collection's own name is
      given.)
    * ``auto_shortflags``: Whether or not to :ref:`automatically create short
      flags <automatic-shortflags>` from task options; defaults to True.
    """
    # @task -- no options
    if len(args) == 1:
        return Task(args[0])
    # @task(options)
    # TODO: pull in centrally defined defaults here (see Task)
    aliases = kwargs.pop('aliases', ())
    positional = kwargs.pop('positional', None)
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
