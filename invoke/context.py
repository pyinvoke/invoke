import getpass
import re

from invoke.vendor.six import raise_from

from .config import Config, DataProxy
from .exceptions import Failure, AuthFailure, ResponseNotAccepted
from .runners import Local
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
    """
    pass
