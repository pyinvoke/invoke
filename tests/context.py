import os
import pickle
import re
import sys

from mock import patch, Mock, call
from spec import Spec, skip, eq_, ok_, trap, raises

from invoke import (
    AuthFailure, Context, Config, FailingResponder, ResponseNotAccepted,
    StreamWatcher, MockContext, Result,
)

from _util import mock_subprocess, _Dummy


local_path = 'invoke.config.Local'


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

        class run:
            # NOTE: actual behavior of command running is tested in runners.py
            def exists(self):
                self._expect_attr('run')

            @patch(local_path)
            def defaults_to_Local(self, Local):
                c = Context()
                c.run('foo')
                assert Local.mock_calls == [
                    call(c), call().run('foo')
                ]

            def honors_runner_config_setting(self):
                runner_class = Mock()
                config = Config({'runners': {'local': runner_class}})
                c = Context(config)
                c.run('foo')
                assert runner_class.mock_calls == [
                    call(c), call().run('foo'),
                ]

        def sudo(self):
            self._expect_attr('sudo')

    class configuration_proxy:
        "Dict-like proxy for self.config"
        def setup(self):
            config = Config(defaults={'foo': 'bar', 'biz': {'baz': 'boz'}})
            self.c = Context(config=config)

        def direct_access_allowed(self):
            eq_(self.c.config.__class__, Config)
            eq_(self.c.config['foo'], 'bar')
            eq_(self.c.config.foo, 'bar')

        def config_attr_may_be_overwritten_at_runtime(self):
            new_config = Config(defaults={'foo': 'notbar'})
            self.c.config = new_config
            eq_(self.c.foo, 'notbar')

        def getitem(self):
            "___getitem__"
            eq_(self.c['foo'], 'bar')
            eq_(self.c['biz']['baz'], 'boz')

        def getattr(self):
            "__getattr__"
            eq_(self.c.foo, 'bar')
            eq_(self.c.biz.baz, 'boz')

        def get(self):
            eq_(self.c.get('foo'), 'bar')
            eq_(self.c.get('nope', 'wut'), 'wut')
            eq_(self.c.biz.get('nope', 'hrm'), 'hrm')

        def pop(self):
            eq_(self.c.pop('foo'), 'bar')
            eq_(self.c.pop('foo', 'notbar'), 'notbar')
            eq_(self.c.biz.pop('baz'), 'boz')

        def popitem(self):
            eq_(self.c.biz.popitem(), ('baz', 'boz'))
            del self.c['biz']
            eq_(self.c.popitem(), ('foo', 'bar'))
            eq_(self.c.config, {})

        def del_(self):
            "del"
            del self.c['foo']
            del self.c['biz']['baz']
            eq_(self.c.biz, {})
            del self.c['biz']
            eq_(self.c.config, {})

        def clear(self):
            self.c.biz.clear()
            eq_(self.c.biz, {})
            self.c.clear()
            eq_(self.c.config, {})

        def setdefault(self):
            eq_(self.c.setdefault('foo'), 'bar')
            eq_(self.c.biz.setdefault('baz'), 'boz')
            eq_(self.c.setdefault('notfoo', 'notbar'), 'notbar')
            eq_(self.c.notfoo, 'notbar')
            eq_(self.c.biz.setdefault('otherbaz', 'otherboz'), 'otherboz')
            eq_(self.c.biz.otherbaz, 'otherboz')

        def update(self):
            self.c.update({'newkey': 'newval'})
            eq_(self.c['newkey'], 'newval')
            eq_(self.c.foo, 'bar')
            self.c.biz.update(otherbaz='otherboz')
            eq_(self.c.biz.otherbaz, 'otherboz')

    class cwd:
        def setup(self):
            self.ctx = Context()

        def simple(self):
            self.ctx.command_cwds = ['a', 'b']
            eq_(self.ctx.cwd, os.path.join('a', 'b'))

        def nested_absolute_path(self):
            self.ctx.command_cwds = ['a', '/b', 'c']
            eq_(self.ctx.cwd, os.path.join('/b', 'c'))

        def multiple_absolute_paths(self):
            self.ctx.command_cwds = ['a', '/b', 'c', '/d', 'e']
            eq_(self.ctx.cwd, os.path.join('/d', 'e'))

        def home(self):
            self.ctx.command_cwds = ['a', '~b', 'c']
            eq_(self.ctx.cwd, os.path.join('~b', 'c'))

    class cd:
        def setup(self):
            self.escaped_prompt = re.escape(Config().sudo.prompt)

        @patch(local_path)
        def cd_should_apply_to_run(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.cd('foo'):
                ctx.run('whoami')

            cmd = "cd foo && whoami"
            ok_(runner.run.called, "run() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def cd_should_apply_to_sudo(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.cd('foo'):
                ctx.sudo('whoami')

            cmd = "sudo -S -p '[sudo] password: ' cd foo && whoami"
            ok_(runner.run.called, "sudo() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def cd_should_occur_before_prefixes(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.prefix('source venv'):
                with ctx.cd('foo'):
                    ctx.run('whoami')

            cmd = "cd foo && source venv && whoami"
            ok_(runner.run.called, "run() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

    class prefix:
        def setup(self):
            self.escaped_prompt = re.escape(Config().sudo.prompt)

        @patch(local_path)
        def prefixes_should_apply_to_run(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.prefix('cd foo'):
                ctx.run('whoami')

            cmd = "cd foo && whoami"
            ok_(runner.run.called, "run() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def prefixes_should_apply_to_sudo(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.prefix('cd foo'):
                ctx.sudo('whoami')

            cmd = "sudo -S -p '[sudo] password: ' cd foo && whoami"
            ok_(runner.run.called, "sudo() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def nesting_should_retain_order(self, Local):
            runner = Local.return_value
            ctx = Context()
            with ctx.prefix('cd foo'):
                with ctx.prefix('cd bar'):
                    ctx.run('whoami')
                    cmd = "cd foo && cd bar && whoami"
                    ok_(runner.run.called, "run() never called runner.run()!")
                    eq_(runner.run.call_args[0][0], cmd)

                ctx.run('whoami')
                cmd = "cd foo && whoami"
                ok_(runner.run.called, "run() never called runner.run()!")
                eq_(runner.run.call_args[0][0], cmd)

            # also test that prefixes do not persist
            ctx.run('whoami')
            cmd = "whoami"
            ok_(runner.run.called, "run() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

    class sudo:
        def setup(self):
            self.escaped_prompt = re.escape(Config().sudo.prompt)

        @patch(local_path)
        def prefixes_command_with_sudo(self, Local):
            runner = Local.return_value
            Context().sudo('whoami')
            # NOTE: implicitly tests default sudo.prompt conf value
            cmd = "sudo -S -p '[sudo] password: ' whoami"
            ok_(runner.run.called, "sudo() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def optional_user_argument_adds_u_and_H_flags(self, Local):
            runner = Local.return_value
            Context().sudo('whoami', user='rando')
            cmd = "sudo -S -p '[sudo] password: ' -H -u rando whoami"
            ok_(runner.run.called, "sudo() never called runner.run()!")
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def honors_config_for_user_value(self, Local):
            runner = Local.return_value
            config = Config(overrides={'sudo': {'user': 'rando'}})
            Context(config=config).sudo('whoami')
            cmd = "sudo -S -p '[sudo] password: ' -H -u rando whoami"
            eq_(runner.run.call_args[0][0], cmd)

        @patch(local_path)
        def user_kwarg_wins_over_config(self, Local):
            runner = Local.return_value
            config = Config(overrides={'sudo': {'user': 'rando'}})
            Context(config=config).sudo('whoami', user='calrissian')
            cmd = "sudo -S -p '[sudo] password: ' -H -u calrissian whoami"
            eq_(runner.run.call_args[0][0], cmd)

        @trap
        @mock_subprocess()
        def echo_hides_extra_sudo_flags(self):
            skip() # see TODO in sudo() re: clean output display
            config = Config(overrides={'runner': _Dummy})
            Context(config=config).sudo('nope', echo=True)
            output = sys.stdout.getvalue()
            sys.__stderr__.write(repr(output) + "\n")
            ok_("-S" not in output)
            ok_(Context().sudo.prompt not in output)
            ok_("sudo nope" in output)

        @patch(local_path)
        def honors_config_for_prompt_value(self, Local):
            runner = Local.return_value
            config = Config(overrides={'sudo': {'prompt': 'FEED ME: '}})
            Context(config=config).sudo('whoami')
            cmd = "sudo -S -p 'FEED ME: ' whoami"
            eq_(runner.run.call_args[0][0], cmd)

        def prompt_value_is_properly_shell_escaped(self):
            # I.e. setting it to "here's johnny!" doesn't explode.
            # NOTE: possibly best to tie into issue #2
            skip()

        def _expect_responses(self, expected, config=None, kwargs=None):
            """
            Execute mocked sudo(), expecting watchers= kwarg in its run().

            * expected: list of 2-tuples of FailingResponder prompt/response
            * config: Config object, if an overridden one is needed
            * kwargs: sudo() kwargs, if needed
            """
            if kwargs is None:
                kwargs = {}
            Local = Mock()
            runner = Local.return_value
            context = Context(config=config) if config else Context()
            context.config.runners.local = Local
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

            @patch(local_path)
            def kwarg_only_adds_to_kwarg(self, Local):
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

            @patch(local_path)
            def config_only(self, Local):
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

            @patch(local_path)
            def config_use_does_not_modify_config(self, Local):
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

            @patch(local_path)
            def both_kwarg_and_config(self, Local):
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

        @patch(local_path)
        def passes_through_other_run_kwargs(self, Local):
            runner = Local.return_value
            Context().sudo(
                'whoami', echo=True, warn=False, hide=True, encoding='ascii'
            )
            ok_(runner.run.called, "sudo() never called runner.run()!")
            kwargs = runner.run.call_args[1]
            eq_(kwargs['echo'], True)
            eq_(kwargs['warn'], False)
            eq_(kwargs['hide'], True)
            eq_(kwargs['encoding'], 'ascii')

        @patch(local_path)
        def returns_run_result(self, Local):
            runner = Local.return_value
            expected = runner.run.return_value
            result = Context().sudo('whoami')
            ok_(
                result is expected,
                "sudo() did not return run()'s return value!",
            )

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

    def can_be_pickled(self):
        c = Context()
        c.foo = {'bar': {'biz': ['baz', 'buzz']}}
        c2 = pickle.loads(pickle.dumps(c))
        eq_(c, c2)
        ok_(c is not c2)
        ok_(c.foo.bar.biz is not c2.foo.bar.biz)


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

    def return_value_kwargs_may_be_command_string_maps(self):
        c = MockContext(run={'foo': Result("bar")})
        eq_(c.run("foo").stdout, "bar")

    def return_value_map_kwargs_may_take_iterables_too(self):
        c = MockContext(run={'foo': [Result("bar"), Result("biz")]})
        eq_(c.run("foo").stdout, "bar")
        eq_(c.run("foo").stdout, "biz")

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

        def mapping_to_single_value(self):
            self._expect_NotImplementedError(MockContext(run={
                "something": Result("meh")
            }))

        def mapping_to_iterable(self):
            self._expect_NotImplementedError(MockContext(run={
                "something": [Result("meh")]
            }))

    @raises(TypeError)
    def unexpected_kwarg_type_yields_TypeError(self):
        MockContext(run=123)

    class can_modify_return_value_maps_after_instantiation:
        class non_dict_type_instantiation_values_yield_TypeErrors:
            class no_stored_result:
                @raises(TypeError)
                def run(self):
                    mc = MockContext()
                    mc.set_result_for('run', 'whatever', Result('bar'))

                @raises(TypeError)
                def sudo(self):
                    mc = MockContext()
                    mc.set_result_for('sudo', 'whatever', Result('bar'))

            class single_result:
                @raises(TypeError)
                def run(self):
                    mc = MockContext(run=Result('foo'))
                    mc.set_result_for('run', 'whatever', Result('bar'))

                @raises(TypeError)
                def sudo(self):
                    mc = MockContext(sudo=Result('foo'))
                    mc.set_result_for('sudo', 'whatever', Result('bar'))

            class iterable_result:
                @raises(TypeError)
                def run(self):
                    mc = MockContext(run=[Result('foo')])
                    mc.set_result_for('run', 'whatever', Result('bar'))

                @raises(TypeError)
                def sudo(self):
                    mc = MockContext(sudo=[Result('foo')])
                    mc.set_result_for('sudo', 'whatever', Result('bar'))

        def run(self):
            mc = MockContext(run={'foo': Result('bar')})
            assert mc.run('foo').stdout == 'bar'
            mc.set_result_for('run', 'foo', Result('biz'))
            assert mc.run('foo').stdout == 'biz'

        def sudo(self):
            mc = MockContext(sudo={'foo': Result('bar')})
            assert mc.sudo('foo').stdout == 'bar'
            mc.set_result_for('sudo', 'foo', Result('biz'))
            assert mc.sudo('foo').stdout == 'biz'
