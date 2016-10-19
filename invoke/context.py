import getpass
import re

from invoke.vendor.six import raise_from, iteritems

from .config import Config, DataProxy
from .exceptions import Failure, AuthFailure, ResponseNotAccepted
from .runners import Local, Result
from .watchers import FailingResponder


class Context(DataProxy):
    """
    Context-aware API wrapper & state-passing object.

    `.Context` objects are created during command-line parsing (or, if desired,
    by hand) and used to share parser and configuration state with executed
    tasks (see :doc:`/concepts/context`).

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime. It also acts as a proxy for its `~.Context.config`
    attribute - see that attribute's documentation for details.

    Instances of `.Context` may be shared between tasks when executing
    sub-tasks - either the same context the caller was given, or an altered
    copy thereof (or, theoretically, a brand new one).
    """
    def __init__(self, config=None):
        """
        :param config:
            `.Config` object to use as the base configuration.

            Defaults to an anonymous/default `.Config` instance.
        """

        #: The fully merged `.Config` object appropriate for this context.
        #:
        #: `.Config` settings (see their documentation for details) may be
        #: accessed like dictionary keys (``ctx.config['foo']``) or object
        #: attributes (``ctx.config.foo``).
        #:
        #: As a convenience shorthand, the `.Context` object proxies to its
        #: ``config`` attribute in the same way - e.g. ``ctx['foo']`` or
        #: ``ctx.foo`` returns the same value as ``ctx.config['foo']``.
        self.config = config if config is not None else Config()

    def run(self, command, **kwargs):
        """
        Execute a local shell command, honoring config options.

        Specifically, this method instantiates a `.Runner` subclass (according
        to the ``runner`` config option; default is `.Local`) and calls its
        ``.run`` method with ``command`` and ``kwargs``.

        See `.Runner.run` for details on ``command`` and the available keyword
        arguments.
        """
        runner_class = self.config.get('runner', Local)
        return runner_class(context=self).run(command, **kwargs)

    def sudo(self, command, **kwargs):
        """
        Execute a shell command, via ``sudo``.

        In general, this method is identical to `run`, but adds a handful of
        convenient behaviors around invoking the ``sudo`` program. It doesn't
        do anything users could not do themselves by wrapping `run`, but the
        use case is too common to make users reinvent these wheels themselves.

        Specifically, `sudo`:

        * Places a `.FailingResponder` into the ``watchers`` kwarg (see
          :doc:`/concepts/watchers`) which:

            * searches for the configured ``sudo`` password prompt;
            * responds with the configured sudo password (``sudo.password``
              from the :doc:`configuration </concepts/configuration>`, or a
              runtime `getpass <getpass.getpass>` input);
            * can tell when that response causes an authentication failure, and
              raises an exception if so.

        * Builds a ``sudo`` command string using the supplied ``command``
          argument prefixed by the ``sudo.prefix`` configuration setting;
        * Executes that command via a call to `run`, returning the result.

        As with `run`, these additional behaviors may be configured both via
        the ``run`` tree of configuration settings (like ``run.echo``) or via
        keyword arguments, which will override the configuration system.

        :param str password: Runtime override for ``sudo.password``.
        :param str prefix: Runtime override for ``sudo.prefix``.
        """
        prompt = self.config.sudo.prompt
        password = kwargs.pop('password', self.config.sudo.password)
        if password is None:
            msg = "No stored sudo password found, please enter it now: "
            # TODO: use something generic/overrideable that uses getpass by
            # default. May mean we pop this out as its own class-as-a-method or
            # something?
            password = getpass.getpass(msg)
        # TODO: want to print a "cleaner" echo with just 'sudo <command>'; but
        # hard to do as-is, obtaining config data from outside a Runner one
        # holds is currently messy (could fix that), if instead we manually
        # inspect the config ourselves that duplicates logic. NOTE: once we
        # figure that out, there is an existing, would-fail-if-not-skipped test
        # for this behavior in test/context.py.
        # TODO: once that is done, though: how to handle "full debug" output
        # exactly (display of actual, real full sudo command w/ -S and -p), in
        # terms of API/config? Impl is easy, just go back to passing echo
        # through to 'run'...
        cmd_str = "sudo -S -p '{0}' {1}".format(prompt, command)
        watcher = FailingResponder(
            pattern=re.escape(prompt),
            response="{0}\n".format(password),
            sentinel="Sorry, try again.\n",
        )
        # Ensure we merge any user-specified watchers with our own.
        # NOTE: If there are config-driven watchers, we pull those up to the
        # kwarg level; that lets us merge cleanly without needing complex
        # config-driven "override vs merge" semantics.
        # TODO: if/when those semantics are implemented, use them instead.
        # NOTE: config value for watchers defaults to an empty list; and we
        # want to clone it to avoid actually mutating the config.
        watchers = kwargs.pop('watchers', list(self.config.run.watchers))
        watchers.append(watcher)
        try:
            return self.run(cmd_str, watchers=watchers, **kwargs)
        except Failure as failure:
            # Transmute failures driven by our FailingResponder, into auth
            # failures - the command never even ran.
            # TODO: wants to be a hook here for users that desire "override a
            # bad config value for sudo.password" manual input
            # NOTE: as noted in #294 comments, we MAY in future want to update
            # this so run() is given ability to raise AuthFailure on its own.
            # For now that has been judged unnecessary complexity.
            if isinstance(failure.reason, ResponseNotAccepted):
                # NOTE: not bothering with 'reason' here, it's pointless.
                # NOTE: using raise_from(..., None) to suppress Python 3's
                # "helpful" multi-exception output. It's confusing here.
                error = AuthFailure(result=failure.result, prompt=prompt)
                raise_from(error, None)
            # Reraise for any other error so it bubbles up normally.
            else:
                raise


class MockContext(Context):
    """
    A `.Context` whose methods' return values can be predetermined.

    Primarily useful for testing Invoke-using codebases.

    .. note::
        Methods not given `Results <.Result>` to yield will raise
        `NotImplementedError` if called (since the alternative is to call the
        real underlying method - typically undesirable when mocking.)
    """
    def __init__(self, config=None, **kwargs):
        """
        Create a ``Context``-like object whose methods yield `.Result` objects.

        :param config:
            A Configuration object to use. Identical in behavior to `.Context`.

        :param run:
            A list of `Results <.Result>`, to yield on each subsequent call to
            the instantiated object's `~.Context.run` method (instead of
            actually calling the requested shell command).

            May supply a `.Result` object in place of list, which acts as
            shorthand for supplying the object inside a one-item list.

        :param sudo:
            Identical to ``run``, but whose values are yielded from calls to
            `~.Context.sudo`.
        """
        # TODO: consider tweaking semantics re: whether a single Result means
        # "yield once" or "yield always". Tradeoff of masking unexpected calls
        # to the method (where 'yield single object/iterable' would make it
        # obvious that the method was called more times than you expected),
        # versus convenience and consistency re: e.g. the 'mock' library.
        # (Counterpoint: users desiring 'yield always' can simply supply
        # itertools.repeat(Result(...))...)
        super(MockContext, self).__init__(config)
        for method, results in iteritems(kwargs):
            # Special convenience case: individual Result -> one-item list
            if isinstance(results, Result):
                results = [results]
            setattr(self, "_{0}".format(method), results)

    # TODO: _maybe_ make this more metaprogrammy/flexible (using __call__ etc)?
    # Pretty worried it'd cause more hard-to-debug issues than it's presently
    # worth. Maybe in situations where Context grows a _lot_ of methods (e.g.
    # in Fabric 2; though Fabric could do its own sub-subclass in that case...)

    def run(self, *args, **kwargs):
        if not hasattr(self, '_run'):
            raise NotImplementedError # We weren't given anything to mock
        # TODO: perform more convenience stuff associating args/kwargs with the
        # result? E.g. filling in .command, etc? Possibly useful for debugging
        # if one hits unexpected-order problems with what they passed in to
        # __init__.
        return self._run.pop(0)

    def sudo(self, *args, **kwargs):
        # TODO: this completely nukes the top-level behavior of sudo(), which
        # could be good or bad, depending. Most of the time I think it's good.
        # No need to supply dummy password config, etc.
        if not hasattr(self, '_sudo'):
            raise NotImplementedError # We weren't given anything to mock
        # TODO: see the TODO from run() re: injecting arg/kwarg values
        return self._sudo.pop(0)
