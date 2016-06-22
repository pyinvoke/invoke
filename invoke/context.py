import getpass
import re

from .runners import Local
from .config import Config, DataProxy


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

        * Updates the value of the ``responses`` dict (see
          :doc:`/concepts/responding`) so that it includes a key for the
          ``sudo`` password prompt.
        * Fills in the value/response for that key from the ``sudo.password``
          :doc:`configuration </concepts/configuration>` setting.

          If *no* config value is found, the user is prompted interactively via
          `getpass <getpass.getpass>`, and the value is stored in memory for
          reuse.
        * Builds a full ``sudo`` command string using the supplied ``command``
          argument prefixed by the ``sudo.prefix`` configuration setting.
        * Executes that command via a call to `run`, returning the result.

        As with `run`, these additional behaviors may be configured both via
        the ``run`` configuration settings (like ``run.echo``) or via runtime
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
        cmd_str = "sudo -S -p '{0}' {1}".format(prompt, command)
        escaped_prompt = re.escape(prompt)
        responses = {escaped_prompt: "{0}\n".format(password)}
        # TODO: we always want our auto-added one merged - how to square that
        # with how kwarg always wins currently?
        # * If we add to self.config, and user gives kwarg, ours is lost
        # * If we add to kwarg, any user config is lost
        return Local(context=self).run(cmd_str, responses=responses, **kwargs)
