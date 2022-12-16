import os
import re
from contextlib import contextmanager
from itertools import cycle

try:
    from invoke.vendor.six import raise_from, iteritems, string_types
except ImportError:
    from six import raise_from, iteritems, string_types

from .config import Config, DataProxy
from .exceptions import Failure, AuthFailure, ResponseNotAccepted
from .runners import Result
from .watchers import FailingResponder


class Context(DataProxy):
    """
    Context-aware API wrapper & state-passing object.

    `.Context` objects are created during command-line parsing (or, if desired,
    by hand) and used to share parser and configuration state with executed
    tasks (see :ref:`why-context`).

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime. It also acts as a proxy for its `~.Context.config`
    attribute - see that attribute's documentation for details.

    Instances of `.Context` may be shared between tasks when executing
    sub-tasks - either the same context the caller was given, or an altered
    copy thereof (or, theoretically, a brand new one).

    .. versionadded:: 1.0
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
        #: accessed like dictionary keys (``c.config['foo']``) or object
        #: attributes (``c.config.foo``).
        #:
        #: As a convenience shorthand, the `.Context` object proxies to its
        #: ``config`` attribute in the same way - e.g. ``c['foo']`` or
        #: ``c.foo`` returns the same value as ``c.config['foo']``.
        config = config if config is not None else Config()
        self._set(_config=config)
        #: A list of commands to run (via "&&") before the main argument to any
        #: `run` or `sudo` calls. Note that the primary API for manipulating
        #: this list is `prefix`; see its docs for details.
        command_prefixes = list()
        self._set(command_prefixes=command_prefixes)
        #: A list of directories to 'cd' into before running commands with
        #: `run` or `sudo`; intended for management via `cd`, please see its
        #: docs for details.
        command_cwds = list()
        self._set(command_cwds=command_cwds)

    @property
    def config(self):
        # Allows Context to expose a .config attribute even though DataProxy
        # otherwise considers it a config key.
        return self._config

    @config.setter
    def config(self, value):
        # NOTE: mostly used by client libraries needing to tweak a Context's
        # config at execution time; i.e. a Context subclass that bears its own
        # unique data may want to be stood up when parameterizing/expanding a
        # call list at start of a session, with the final config filled in at
        # runtime.
        self._set(_config=value)

    def run(self, command, **kwargs):
        """
        Execute a local shell command, honoring config options.

        Specifically, this method instantiates a `.Runner` subclass (according
        to the ``runner`` config option; default is `.Local`) and calls its
        ``.run`` method with ``command`` and ``kwargs``.

        See `.Runner.run` for details on ``command`` and the available keyword
        arguments.

        .. versionadded:: 1.0
        """
        runner = self.config.runners.local(self)
        return self._run(runner, command, **kwargs)

    # NOTE: broken out of run() to allow for runner class injection in
    # Fabric/etc, which needs to juggle multiple runner class types (local and
    # remote).
    def _run(self, runner, command, **kwargs):
        command = self._prefix_commands(command)
        return runner.run(command, **kwargs)

    def sudo(self, command, **kwargs):
        """
        Execute a shell command via ``sudo`` with password auto-response.

        **Basics**

        This method is identical to `run` but adds a handful of
        convenient behaviors around invoking the ``sudo`` program. It doesn't
        do anything users could not do themselves by wrapping `run`, but the
        use case is too common to make users reinvent these wheels themselves.

        .. note::
            If you intend to respond to sudo's password prompt by hand, just
            use ``run("sudo command")`` instead! The autoresponding features in
            this method will just get in your way.

        Specifically, `sudo`:

        * Places a `.FailingResponder` into the ``watchers`` kwarg (see
          :doc:`/concepts/watchers`) which:

            * searches for the configured ``sudo`` password prompt;
            * responds with the configured sudo password (``sudo.password``
              from the :doc:`configuration </concepts/configuration>`);
            * can tell when that response causes an authentication failure
              (e.g. if the system requires a password and one was not
              configured), and raises `.AuthFailure` if so.

        * Builds a ``sudo`` command string using the supplied ``command``
          argument, prefixed by various flags (see below);
        * Executes that command via a call to `run`, returning the result.

        **Flags used**

        ``sudo`` flags used under the hood include:

        - ``-S`` to allow auto-responding of password via stdin;
        - ``-p <prompt>`` to explicitly state the prompt to use, so we can be
          sure our auto-responder knows what to look for;
        - ``-u <user>`` if ``user`` is not ``None``, to execute the command as
          a user other than ``root``;
        - When ``-u`` is present, ``-H`` is also added, to ensure the
          subprocess has the requested user's ``$HOME`` set properly.

        **Configuring behavior**

        There are a couple of ways to change how this method behaves:

        - Because it wraps `run`, it honors all `run` config parameters and
          keyword arguments, in the same way that `run` does.

            - Thus, invocations such as ``c.sudo('command', echo=True)`` are
              possible, and if a config layer (such as a config file or env
              var) specifies that e.g. ``run.warn = True``, that too will take
              effect under `sudo`.

        - `sudo` has its own set of keyword arguments (see below) and they are
          also all controllable via the configuration system, under the
          ``sudo.*`` tree.

            - Thus you could, for example, pre-set a sudo user in a config
              file; such as an ``invoke.json`` containing ``{"sudo": {"user":
              "someuser"}}``.

        :param str password: Runtime override for ``sudo.password``.
        :param str user: Runtime override for ``sudo.user``.

        .. versionadded:: 1.0
        """
        runner = self.config.runners.local(self)
        return self._sudo(runner, command, **kwargs)

    # NOTE: this is for runner injection; see NOTE above _run().
    def _sudo(self, runner, command, **kwargs):
        prompt = self.config.sudo.prompt
        password = kwargs.pop("password", self.config.sudo.password)
        user = kwargs.pop("user", self.config.sudo.user)
        env = kwargs.get("env", {})
        # TODO: allow subclassing for 'get the password' so users who REALLY
        # want lazy runtime prompting can have it easily implemented.
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
        user_flags = ""
        if user is not None:
            user_flags = "-H -u {} ".format(user)
        env_flags = ""
        if env:
            env_flags = "--preserve-env='{}' ".format(",".join(env.keys()))
        command = self._prefix_commands(command)
        cmd_str = "sudo -S -p '{}' {}{}{}".format(
            prompt, env_flags, user_flags, command
        )
        watcher = FailingResponder(
            pattern=re.escape(prompt),
            response="{}\n".format(password),
            sentinel="Sorry, try again.\n",
        )
        # Ensure we merge any user-specified watchers with our own.
        # NOTE: If there are config-driven watchers, we pull those up to the
        # kwarg level; that lets us merge cleanly without needing complex
        # config-driven "override vs merge" semantics.
        # TODO: if/when those semantics are implemented, use them instead.
        # NOTE: config value for watchers defaults to an empty list; and we
        # want to clone it to avoid actually mutating the config.
        watchers = kwargs.pop("watchers", list(self.config.run.watchers))
        watchers.append(watcher)
        try:
            return runner.run(cmd_str, watchers=watchers, **kwargs)
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

    # TODO: wonder if it makes sense to move this part of things inside Runner,
    # which would grow a `prefixes` and `cwd` init kwargs or similar. The less
    # that's stuffed into Context, probably the better.
    def _prefix_commands(self, command):
        """
        Prefixes ``command`` with all prefixes found in ``command_prefixes``.

        ``command_prefixes`` is a list of strings which is modified by the
        `prefix` context manager.
        """
        prefixes = list(self.command_prefixes)
        current_directory = self.cwd
        if current_directory:
            prefixes.insert(0, "cd {}".format(current_directory))

        return " && ".join(prefixes + [command])

    @contextmanager
    def prefix(self, command):
        """
        Prefix all nested `run`/`sudo` commands with given command plus ``&&``.

        Most of the time, you'll want to be using this alongside a shell script
        which alters shell state, such as ones which export or alter shell
        environment variables.

        For example, one of the most common uses of this tool is with the
        ``workon`` command from `virtualenvwrapper
        <https://virtualenvwrapper.readthedocs.io/en/latest/>`_::

            with c.prefix('workon myvenv'):
                c.run('./manage.py migrate')

        In the above snippet, the actual shell command run would be this::

            $ workon myvenv && ./manage.py migrate

        This context manager is compatible with `cd`, so if your virtualenv
        doesn't ``cd`` in its ``postactivate`` script, you could do the
        following::

            with c.cd('/path/to/app'):
                with c.prefix('workon myvenv'):
                    c.run('./manage.py migrate')
                    c.run('./manage.py loaddata fixture')

        Which would result in executions like so::

            $ cd /path/to/app && workon myvenv && ./manage.py migrate
            $ cd /path/to/app && workon myvenv && ./manage.py loaddata fixture

        Finally, as alluded to above, `prefix` may be nested if desired, e.g.::

            with c.prefix('workon myenv'):
                c.run('ls')
                with c.prefix('source /some/script'):
                    c.run('touch a_file')

        The result::

            $ workon myenv && ls
            $ workon myenv && source /some/script && touch a_file

        Contrived, but hopefully illustrative.

        .. versionadded:: 1.0
        """
        self.command_prefixes.append(command)
        try:
            yield
        finally:
            self.command_prefixes.pop()

    @property
    def cwd(self):
        """
        Return the current working directory, accounting for uses of `cd`.

        .. versionadded:: 1.0
        """
        if not self.command_cwds:
            # TODO: should this be None? Feels cleaner, though there may be
            # benefits to it being an empty string, such as relying on a no-arg
            # `cd` typically being shorthand for "go to user's $HOME".
            return ""

        # get the index for the subset of paths starting with the last / or ~
        for i, path in reversed(list(enumerate(self.command_cwds))):
            if path.startswith("~") or path.startswith("/"):
                break

        # TODO: see if there's a stronger "escape this path" function somewhere
        # we can reuse. e.g., escaping tildes or slashes in filenames.
        paths = [path.replace(" ", r"\ ") for path in self.command_cwds[i:]]
        return os.path.join(*paths)

    @contextmanager
    def cd(self, path):
        """
        Context manager that keeps directory state when executing commands.

        Any calls to `run`, `sudo`, within the wrapped block will implicitly
        have a string similar to ``"cd <path> && "`` prefixed in order to give
        the sense that there is actually statefulness involved.

        Because use of `cd` affects all such invocations, any code making use
        of the `cwd` property will also be affected by use of `cd`.

        Like the actual 'cd' shell builtin, `cd` may be called with relative
        paths (keep in mind that your default starting directory is your user's
        ``$HOME``) and may be nested as well.

        Below is a "normal" attempt at using the shell 'cd', which doesn't work
        since all commands are executed in individual subprocesses -- state is
        **not** kept between invocations of `run` or `sudo`::

            c.run('cd /var/www')
            c.run('ls')

        The above snippet will list the contents of the user's ``$HOME``
        instead of ``/var/www``. With `cd`, however, it will work as expected::

            with c.cd('/var/www'):
                c.run('ls')  # Turns into "cd /var/www && ls"

        Finally, a demonstration (see inline comments) of nesting::

            with c.cd('/var/www'):
                c.run('ls') # cd /var/www && ls
                with c.cd('website1'):
                    c.run('ls')  # cd /var/www/website1 && ls

        .. note::
            Space characters will be escaped automatically to make dealing with
            such directory names easier.

        .. versionadded:: 1.0
        .. versionchanged:: 1.5
            Explicitly cast the ``path`` argument (the only argument) to a
            string; this allows any object defining ``__str__`` to be handed in
            (such as the various ``Path`` objects out there), and not just
            string literals.
        """
        path = str(path)
        self.command_cwds.append(path)
        try:
            yield
        finally:
            self.command_cwds.pop()


class MockContext(Context):
    """
    A `.Context` whose methods' return values can be predetermined.

    Primarily useful for testing Invoke-using codebases.

    .. note::
        If this class' constructor is able to import the ``Mock`` class at
        runtime (via the ``mock`` or ``unittest.mock`` modules, in that order)
        it will wraps its ``run``, etc methods in ``Mock`` objects. This allows
        you to easily assert that the methods (still returning the values you
        prepare them with) were actually called.

    .. note::
        Methods not given `Results <.Result>` to yield will raise
        ``NotImplementedError`` if called (since the alternative is to call the
        real underlying method - typically undesirable when mocking.)

    .. versionadded:: 1.0
    .. versionchanged:: 1.5
        Added conditional ``Mock`` wrapping of ``run`` and ``sudo``.
    """

    def __init__(self, config=None, **kwargs):
        """
        Create a ``Context``-like object whose methods yield `.Result` objects.

        :param config:
            A Configuration object to use. Identical in behavior to `.Context`.

        :param run:
            A data structure indicating what `.Result` objects to return from
            calls to the instantiated object's `~.Context.run` method (instead
            of actually executing the requested shell command).

            Specifically, this kwarg accepts:

            - A single `.Result` object.
            - A boolean; if True, yields a `.Result` whose ``exited`` is ``0``,
              and if False, ``1``.
            - An iterable of the above values, which will be returned on each
              subsequent call to ``.run`` (the first item on the first call,
              the second on the second call, etc).
            - A dict mapping command strings or compiled regexen to the above
              values (including an iterable), allowing specific
              call-and-response semantics instead of assuming a call order.

        :param sudo:
            Identical to ``run``, but whose values are yielded from calls to
            `~.Context.sudo`.

        :param bool repeat:
            A flag determining whether results yielded by this class' methods
            repeat or are consumed.

            For example, when a single result is indicated, it will normally
            only be returned once, causing ``NotImplementedError`` afterwards.
            But when ``repeat=True`` is given, that result is returned on
            every call, forever.

            Similarly, iterable results are normally exhausted once, but when
            this setting is enabled, they are wrapped in `itertools.cycle`.

            Default: ``False`` (for backwards compatibility reasons).

        :raises:
            ``TypeError``, if the values given to ``run`` or other kwargs
            aren't of the expected types.

        .. versionchanged:: 1.5
            Added support for boolean and string result values.
        .. versionchanged:: 1.5
            Added support for regex dict keys.
        .. versionchanged:: 1.5
            Added the ``repeat`` keyword argument.
        """
        # Figure out if we can support Mock in the current environment
        Mock = None
        try:
            from mock import Mock
        except ImportError:
            try:
                from unittest.mock import Mock
            except ImportError:
                pass
        # Set up like any other Context would, with the config
        super(MockContext, self).__init__(config)
        # Pull out behavioral kwargs
        # TODO 2.0: Jesus tap-dancing Christ this needs to default to True, it
        # gets me every single time
        self._set("__repeat", kwargs.pop("repeat", False))
        # The rest must be things like run/sudo - mock Context method info
        for method, results in iteritems(kwargs):
            # For each possible value type, normalize to iterable of Result
            # objects (possibly repeating).
            singletons = tuple([Result, bool] + list(string_types))
            if isinstance(results, dict):
                for key, value in iteritems(results):
                    results[key] = self._normalize(value)
            elif isinstance(results, singletons) or hasattr(
                results, "__iter__"
            ):
                results = self._normalize(results)
            # Unknown input value: cry
            else:
                err = "Not sure how to yield results from a {!r}"
                raise TypeError(err.format(type(results)))
            # Save results for use by the method
            self._set("__{}".format(method), results)
            # Wrap the method in a Mock, if applicable
            if Mock is not None:
                self._set(method, Mock(wraps=getattr(self, method)))

    def _normalize(self, value):
        # First turn everything into an iterable
        if not hasattr(value, "__iter__") or isinstance(value, string_types):
            value = [value]
        # Then turn everything within into a Result
        results = []
        for obj in value:
            if isinstance(obj, bool):
                obj = Result(exited=0 if obj else 1)
            elif isinstance(obj, string_types):
                obj = Result(obj)
            results.append(obj)
        # Finally, turn that iterable into an iteratOR, depending on repeat
        return cycle(results) if getattr(self, "__repeat") else iter(results)

    # TODO: _maybe_ make this more metaprogrammy/flexible (using __call__ etc)?
    # Pretty worried it'd cause more hard-to-debug issues than it's presently
    # worth. Maybe in situations where Context grows a _lot_ of methods (e.g.
    # in Fabric 2; though Fabric could do its own sub-subclass in that case...)

    def _yield_result(self, attname, command):
        try:
            obj = getattr(self, attname)
            # Dicts need to try direct lookup or regex matching
            if isinstance(obj, dict):
                try:
                    obj = obj[command]
                except KeyError:
                    # TODO: could optimize by skipping this if not any regex
                    # objects in keys()?
                    for key, value in iteritems(obj):
                        if hasattr(key, "match") and key.match(command):
                            obj = value
                            break
                    else:
                        # Nope, nothing did match.
                        raise KeyError
            # Here, the value was either never a dict or has been extracted
            # from one, so we can assume it's an iterable of Result objects due
            # to work done by __init__.
            result = next(obj)
            # Populate Result's command string with what matched unless
            # explicitly given
            if not result.command:
                result.command = command
            return result
        except (AttributeError, IndexError, KeyError, StopIteration):
            raise_from(NotImplementedError(command), None)

    def run(self, command, *args, **kwargs):
        # TODO: perform more convenience stuff associating args/kwargs with the
        # result? E.g. filling in .command, etc? Possibly useful for debugging
        # if one hits unexpected-order problems with what they passed in to
        # __init__.
        return self._yield_result("__run", command)

    def sudo(self, command, *args, **kwargs):
        # TODO: this completely nukes the top-level behavior of sudo(), which
        # could be good or bad, depending. Most of the time I think it's good.
        # No need to supply dummy password config, etc.
        # TODO: see the TODO from run() re: injecting arg/kwarg values
        return self._yield_result("__sudo", command)

    def set_result_for(self, attname, command, result):
        """
        Modify the stored mock results for given ``attname`` (e.g. ``run``).

        This is similar to how one instantiates `MockContext` with a ``run`` or
        ``sudo`` dict kwarg. For example, this::

            mc = MockContext(run={'mycommand': Result("mystdout")})
            assert mc.run('mycommand').stdout == "mystdout"

        is functionally equivalent to this::

            mc = MockContext()
            mc.set_result_for('run', 'mycommand', Result("mystdout"))
            assert mc.run('mycommand').stdout == "mystdout"

        `set_result_for` is mostly useful for modifying an already-instantiated
        `MockContext`, such as one created by test setup or helper methods.

        .. versionadded:: 1.0
        """
        attname = "__{}".format(attname)
        heck = TypeError(
            "Can't update results for non-dict or nonexistent mock results!"
        )
        # Get value & complain if it's not a dict.
        # TODO: should we allow this to set non-dict values too? Seems vaguely
        # pointless, at that point, just make a new MockContext eh?
        try:
            value = getattr(self, attname)
        except AttributeError:
            raise heck
        if not isinstance(value, dict):
            raise heck
        # OK, we're good to modify, so do so.
        value[command] = self._normalize(result)
