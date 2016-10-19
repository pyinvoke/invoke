import re
import sys

from mock import patch, Mock
from spec import Spec, skip, eq_, ok_, trap, raises

from invoke import (
    AuthFailure, Context, Config, FailingResponder, ResponseNotAccepted,
    StreamWatcher, MockContext, Result,
)

from _util import mock_subprocess, _Dummy


class Context_(Spec):
    class init:
        "__init__"
        def takes_optional_config_arg(self):
            # Meh-tastic doesn't-barf tests. MEH.
            Context()
            Context(config={'foo': 'bar'})

    class methods_exposed:
        def _expect_attr(self, attr):
            c = Context()
            ok_(hasattr(c, attr) and callable(getattr(c, attr)))

        # NOTE: actual behavior of command running is tested in runners.py
        def run(self):
            self._expect_attr('run')

        def sudo(self):
            self._expect_attr('sudo')

    class configuration_proxy:
        "Dict-like proxy for self.config"
        def setup(self):
            config = Config({'foo': 'bar'})
            self.c = Context(config=config)

        def direct_access_allowed(self):
            eq_(self.c.config.__class__, Config)
            eq_(self.c.config['foo'], 'bar')
            eq_(self.c.config.foo, 'bar')

        def getitem(self):
            "___getitem__"
            eq_(self.c['foo'], 'bar')

        def getattr(self):
            "__getattr__"
            eq_(self.c.foo, 'bar')

        def get(self):
            eq_(self.c.get('foo'), 'bar')
            eq_(self.c.get('biz', 'baz'), 'baz')

        def keys(self):
            skip()

        def values(self):
            skip()

        def iter(self):
            "__iter__"
            skip()

        def update(self):
            self.c.update({'newkey': 'newval'})
            eq_(self.c['newkey'], 'newval')

    class sudo:
        def setup(self):
            self.escaped_prompt = re.escape(Config().sudo.prompt)

        @patch('invoke.context.getpass')
        @patch('invoke.context.Local')
        def prefixes_command_with_sudo(self, Local, getpass):
            runner = Local.return_value
            Context().sudo('whoami')
            # NOTE: implicitly tests default sudo.prompt conf value
            cmd = "sudo -S -p '[sudo] password: ' whoami"
            ok_(runner.run.called, "sudo() never called run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @trap
        @patch('invoke.context.getpass')
        @mock_subprocess()
        def echo_hides_extra_sudo_flags(self, getpass):
            skip() # see TODO in sudo() re: clean output display
            config = Config(overrides={'runner': _Dummy})
            Context(config=config).sudo('nope', echo=True)
            output = sys.stdout.getvalue()
            sys.__stderr__.write(repr(output) + "\n")
            ok_("-S" not in output)
            ok_(Context().sudo.prompt not in output)
            ok_("sudo nope" in output)

        @patch('invoke.context.getpass')
        @patch('invoke.context.Local')
        def honors_config_for_prompt_value(self, Local, getpass):
            runner = Local.return_value
            config = Config(overrides={'sudo': {'prompt': 'FEED ME: '}})
            Context(config=config).sudo('whoami')
            cmd = "sudo -S -p 'FEED ME: ' whoami"
            eq_(runner.run.call_args[0][0], cmd)

        def prompt_value_is_properly_shell_escaped(self):
            # I.e. setting it to "here's johnny!" doesn't explode.
            # NOTE: possibly best to tie into issue #2
            skip()

        @patch('invoke.context.getpass')
        @patch('invoke.context.Local')
        def _expect_responses(self,
            expected, Local, getpass,
            config=None, kwargs=None, getpass_reply=None,
        ):
            """
            Execute mocked sudo(), expecting watchers= kwarg in its run().

            * expected: list of 2-tuples of FailingResponder prompt/response
            * config: Config object, if an overridden one is needed
            * kwargs: sudo() kwargs, if needed
            * getpass_reply: return value of getpass.getpass, if needed

            (Local and getpass are just mock injections.)
            """
            if kwargs is None:
                kwargs = {}
            getpass.getpass.return_value = getpass_reply
            runner = Local.return_value
            context = Context(config=config) if config else Context()
            context.sudo('whoami', **kwargs)
            # Tease out the interesting bits - pattern/response - ignoring the
            # sentinel, etc for now.
            prompt_responses = [
                (watcher.pattern, watcher.response)
                for watcher in runner.run.call_args[1]['watchers']
            ]
            eq_(prompt_responses, expected)

        def autoresponds_with_password_kwarg(self):
            # NOTE: technically duplicates the unitty test(s) in watcher tests.
            expected = [(self.escaped_prompt, 'secret\n')]
            self._expect_responses(expected, kwargs={'password': 'secret'})

        def honors_configured_sudo_password(self):
            config = Config(overrides={'sudo': {'password': 'secret'}})
            expected = [(self.escaped_prompt, 'secret\n')]
            self._expect_responses(expected, config=config)

        def sudo_password_kwarg_wins_over_config(self):
            config = Config(overrides={'sudo': {'password': 'notsecret'}})
            kwargs = {'password': 'secret'}
            expected = [(self.escaped_prompt, 'secret\n')]
            self._expect_responses(expected, config=config, kwargs=kwargs)

        class auto_response_merges_with_other_responses:
            def setup(self):
                class DummyWatcher(StreamWatcher):
                    def submit(self, stream):
                        pass
                self.watcher_klass = DummyWatcher

            @patch('invoke.context.Local')
            @patch('invoke.context.getpass')
            def kwarg_only_adds_to_kwarg(self, getpass, Local):
                runner = Local.return_value
                context = Context()
                watcher = self.watcher_klass()
                context.sudo('whoami', watchers=[watcher])
                # When sudo() called w/ user-specified watchers, we add ours to
                # that list
                watchers = runner.run.call_args[1]['watchers']
                # Will raise ValueError if not in the list
                watchers.remove(watcher)
                # Only remaining item in list should be our sudo responder
                eq_(len(watchers), 1)
                ok_(isinstance(watchers[0], FailingResponder))
                eq_(watchers[0].pattern, self.escaped_prompt)

            @patch('invoke.context.Local')
            @patch('invoke.context.getpass')
            def config_only(self, getpass, Local):
                runner = Local.return_value
                # Set a config-driven list of watchers
                watcher = self.watcher_klass()
                overrides = {'run': {'watchers': [watcher]}}
                config = Config(overrides=overrides)
                Context(config=config).sudo('whoami')
                # Expect that sudo() extracted that config value & put it into
                # the kwarg level. (See comment in sudo() about why...)
                watchers = runner.run.call_args[1]['watchers']
                # Will raise ValueError if not in the list
                watchers.remove(watcher)
                # Only remaining item in list should be our sudo responder
                eq_(len(watchers), 1)
                ok_(isinstance(watchers[0], FailingResponder))
                eq_(watchers[0].pattern, self.escaped_prompt)

            @patch('invoke.context.Local')
            @patch('invoke.context.getpass')
            def config_use_does_not_modify_config(self, getpass, Local):
                runner = Local.return_value
                watcher = self.watcher_klass()
                overrides = {'run': {'watchers': [watcher]}}
                config = Config(overrides=overrides)
                Context(config=config).sudo('whoami')
                # Here, 'watchers' is _the same object_ as was passed into
                # run(watchers=...).
                watchers = runner.run.call_args[1]['watchers']
                # We want to make sure that what's in the config we just
                # generated, is untouched by the manipulation done inside
                # sudo().
                # First, that they aren't the same obj
                err = "Found sudo() reusing config watchers list directly!"
                ok_(watchers is not config.run.watchers, err)
                # And that the list is as it was before (i.e. it is not both
                # our watcher and the sudo()-added one)
                err = "Our config watchers list was modified!"
                eq_(config.run.watchers, [watcher], err)

            @patch('invoke.context.Local')
            @patch('invoke.context.getpass')
            def both_kwarg_and_config(self, getpass, Local):
                runner = Local.return_value
                # Set a config-driven list of watchers
                conf_watcher = self.watcher_klass()
                overrides = {'run': {'watchers': [conf_watcher]}}
                config = Config(overrides=overrides)
                # AND supply a DIFFERENT kwarg-driven list of watchers
                kwarg_watcher = self.watcher_klass()
                Context(config=config).sudo('whoami', watchers=[kwarg_watcher])
                # Expect that the kwarg watcher and our internal one were the
                # final result.
                watchers = runner.run.call_args[1]['watchers']
                # Will raise ValueError if not in the list. .remove() uses
                # identity testing, so two instances of self.watcher_klass will
                # be different values here.
                watchers.remove(kwarg_watcher)
                # Only remaining item in list should be our sudo responder
                eq_(len(watchers), 1)
                ok_(conf_watcher not in watchers) # Extra sanity
                ok_(isinstance(watchers[0], FailingResponder))
                eq_(watchers[0].pattern, self.escaped_prompt)

        def prompts_when_no_configured_password_is_found(self):
            expected = [(self.escaped_prompt, "dynamic\n")]
            self._expect_responses(expected, getpass_reply="dynamic")

        @patch('invoke.context.getpass')
        @patch('invoke.context.Local')
        def passes_through_other_run_kwargs(self, Local, getpass):
            runner = Local.return_value
            Context().sudo(
                'whoami', echo=True, warn=False, hide=True, encoding='ascii'
            )
            ok_(runner.run.called, "sudo() never called run()!")
            kwargs = runner.run.call_args[1]
            eq_(kwargs['echo'], True)
            eq_(kwargs['warn'], False)
            eq_(kwargs['hide'], True)
            eq_(kwargs['encoding'], 'ascii')

        @mock_subprocess(out="something", exit=None)
        def raises_auth_failure_when_failure_detected(self):
            with patch('invoke.context.FailingResponder') as klass:
                unacceptable = Mock(side_effect=ResponseNotAccepted)
                klass.return_value.submit = unacceptable
                excepted = False
                try:
                    config = Config(overrides={'sudo': {'password': 'nope'}})
                    Context(config=config).sudo('meh', hide=True)
                except AuthFailure as e:
                    # Basic sanity checks; most of this is really tested in
                    # Runner tests.
                    eq_(e.result.exited, None)
                    expected = "The password submitted to prompt '[sudo] password: ' was rejected." # noqa
                    eq_(str(e), expected)
                    excepted = True
                # Can't use except/else as that masks other real exceptions,
                # such as incorrectly unhandled ThreadErrors
                if not excepted:
                    assert False, "Did not raise AuthFailure!"


class MockContext_(Spec):
    def init_still_acts_like_superclass_init(self):
        # No required args
        ok_(isinstance(MockContext().config, Config))
        config = Config(overrides={'foo': 'bar'})
        # Posarg
        ok_(MockContext(config).config is config)
        # Kwarg
        ok_(MockContext(config=config).config is config)

    def non_config_init_kwargs_used_as_return_values_for_methods(self):
        c = MockContext(run=Result("some output"))
        eq_(c.run("doesn't mattress").stdout, "some output")

    def return_value_kwargs_can_take_iterables_too(self):
        c = MockContext(run=[Result("some output"), Result("more!")])
        eq_(c.run("doesn't mattress").stdout, "some output")
        eq_(c.run("still doesn't mattress").stdout, "more!")

    @raises(NotImplementedError)
    def methods_with_no_kwarg_values_raise_NotImplementedError(self):
        MockContext().run("onoz I did not anticipate this would happen")

    def sudo_also_covered(self):
        c = MockContext(sudo=Result(stderr="super duper"))
        eq_(c.sudo("doesn't mattress").stderr, "super duper")
        try:
            MockContext().sudo("meh")
        except NotImplementedError:
            pass
        else:
            assert False, "Did not get a NotImplementedError for sudo!"

    class exhausted_return_values_also_raise_NotImplementedError:
        def _expect_NotImplementedError(self, context):
            context.run("something")
            try:
                context.run("something")
            except NotImplementedError:
                pass
            else:
                assert False, "Didn't raise NotImplementedError"

        def single_value(self):
            self._expect_NotImplementedError(MockContext(run=Result("meh")))

        def iterable(self):
            self._expect_NotImplementedError(MockContext(run=[Result("meh")]))

    @raises(TypeError)
    def unexpected_kwarg_type_yields_TypeError(self):
        MockContext(run=123)
