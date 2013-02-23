"""
Task definition & manipulation
"""
import inspect
import types

from .vendor.lexicon import Lexicon

from .compat import zip_longest
from .parser import Argument


# Non-None sentinel
NO_DEFAULT = object()


class Task(object):
    """
    Core object representing an executable task & its argument specification.
    """
    # TODO: store these kwarg defaults central, refer to those values both here
    # and in @task.
    # TODO: allow central per-session / per-taskmodule control over some of
    # them, e.g. (auto_)positional, auto_shortflags.
    # NOTE: we shadow __builtins__.help here. It's purposeful. :(
    def __init__(self, body, aliases=(), positional=None, default=False, 
        auto_shortflags=True, help=None, pre=None):
        self.body = body
        # Must copy doc/name here because Sphinx is retarded about properties.
        self.__doc__ = getattr(body, '__doc__', '')
        self.__name__ = getattr(body, '__name__', '')
        self.aliases = aliases
        self.positional = self.fill_implicit_positionals(positional)
        self.is_default = default
        self.auto_shortflags = auto_shortflags
        self.help = help or {}
        self.pre = pre or []
        self.times_called = 0

    def __call__(self, *args, **kwargs):
        result = self.body(*args, **kwargs)
        self.times_called += 1
        return result

    @property
    def called(self):
        return self.times_called > 0

    def argspec(self, body):
        """
        Returns two-tuple:

        * First item is list of arg names, in order defined.
        * Second item is dict mapping arg names to default values or
          task.NO_DEFAULT (i.e. an 'empty' value distinct from None).
        """
        # Handle callable-but-not-function objects
        # TODO: __call__ exhibits the 'self' arg; do we manually nix 1st result
        # in argspec, or is there a way to get the "really callable" spec?
        func = body if isinstance(body, types.FunctionType) else body.__call__
        spec = inspect.getargspec(func)
        arg_names = spec.args[:]
        matched_args = [reversed(x) for x in [spec.args, spec.defaults or []]]
        spec_dict = dict(zip_longest(*matched_args, fillvalue=NO_DEFAULT))
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
        # Help
        if name in self.help:
            opts['help'] = self.help[name]
        # Whether it's positional or not
        opts['positional'] = name in self.positional
        return opts

    def get_arguments(self):
        """
        Return a list of Argument objects representing this task's signature.
        """
        arg_names, spec_dict = self.argspec(self.body)
        # Obtain list of args + their default values (if any) in
        # declaration/definition order (i.e. based on getargspec())
        tuples = [(x, spec_dict[x]) for x in arg_names]
        # Prime the list of all already-taken names (mostly for help in
        # choosing auto shortflags)
        taken_names = set(x[0] for x in tuples)
        # Build arg list (arg_opts will take care of setting up shortnames,
        # etc)
        args = []
        for name, default in tuples:
            new_arg = Argument(**self.arg_opts(name, default, taken_names))
            args.append(new_arg)
            # Update taken_names list with new argument's full name list
            # (which may include new shortflags) so subsequent Argument
            # creation knows what's taken.
            taken_names.update(set(new_arg.names))
        # Now we need to ensure positionals end up in the front of the list, in
        # order given in self.positionals, so that when Context consumes them,
        # this order is preserved.
        for posarg in reversed(self.positional):
            for i, arg in enumerate(args):
                if arg.name == posarg:
                    args.insert(0, args.pop(i))
                    break
        return args


def task(*args, **kwargs):
    """
    Marks wrapped callable object as a valid Invoke task.

    May be called without any parentheses if no extra options need to be
    specified. Otherwise, the following keyword arguments are allowed in the
    parenthese'd form:

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
    * ``help``: Dict mapping argument names to their help strings. Will be
      displayed in ``--help`` output.
    * ``pre``: List of task names, for tasks that should get run prior to the
      wrapped task whenever it is executed via the command line.

    If any non-keyword arguments are given, they are taken as the value of the
    ``pre`` kwarg for convenience's sake. (It is an error to give both
    ``*args`` and ``pre`` at the same time.)
    """
    # @task -- no options
    if len(args) == 1 and callable(args[0]):
        return Task(args[0])
    # @task(pre, tasks, here)
    if args:
        if 'pre' in kwargs:
            raise TypeError("May not give *args and 'pre' kwarg simultaneously!")
        kwargs['pre'] = args
    # @task(options)
    # TODO: pull in centrally defined defaults here (see Task)
    aliases = kwargs.pop('aliases', ())
    positional = kwargs.pop('positional', None)
    default = kwargs.pop('default', False)
    auto_shortflags = kwargs.pop('auto_shortflags', True)
    help = kwargs.pop('help', {})
    pre = kwargs.pop('pre', [])
    # Handle unknown kwargs
    if kwargs:
        kwarg = (" unknown kwargs %r" % (kwargs,)) if kwargs else ""
        raise TypeError("@task was called with" + kwarg)
    def inner(obj):
        obj = Task(
            obj,
            aliases=aliases,
            positional=positional,
            default=default,
            auto_shortflags=auto_shortflags,
            help=help,
            pre=pre
        )
        return obj
    return inner
