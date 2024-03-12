import os
import pickle
import re
import sys

from unittest.mock import patch, Mock, call
from pytest_relaxed import trap
from pytest import skip, raises, mark

from invoke import (
    AuthFailure,
    Context,
    Config,
    FailingResponder,
    ResponseNotAccepted,
    StreamWatcher,
    MockContext,
    Result,
)

from _util import mock_subprocess, _Dummy


local_path = "invoke.config.Local"
_escaped_prompt = re.escape(Config().sudo.prompt)


class Context_:
    class init:
        "__init__"

        def takes_optional_config_arg(self):
            # Meh-tastic doesn't-barf tests. MEH.
            Context()
            Context(config={"foo": "bar"})

    class methods_exposed:
        def _expect_attr(self, attr):
            c = Context()
            assert hasattr(c, attr) and callable(getattr(c, attr))

        class run:
            # NOTE: actual behavior of command running is tested in runners.py
            def exists(self):
                self._expect_attr("run")

            @patch(local_path)
            def defaults_to_Local(self, Local):
                c = Context()
                c.run("foo")
                assert Local.mock_calls == [call(c), call().run("foo")]

            def honors_runner_config_setting(self):
                runner_class = Mock()
                config = Config({"runners": {"local": runner_class}})
                c = Context(config)
                c.run("foo")
                assert runner_class.mock_calls == [call(c), call().run("foo")]

            @patch(local_path)
            def converts_command_list_to_str(self, Local):
                runner = Local.return_value
                c = Context()
                c.run(["foo", "bar", "baz"])
                cmd = "foo bar baz"
                assert runner.run.called, "run() never called runner.run()!"
                assert runner.run.call_args[0][0] == cmd

        class sudo:
            def exists(self):
                self._expect_attr("sudo")

            @patch(local_path)
            def converts_command_list_to_str(self, Local):
                runner = Local.return_value
                c = Context()
                c.sudo(["foo", "bar", "baz"])
                cmd = "sudo -S -p '[sudo] password: ' foo bar baz"
                assert runner.run.called, "run() never called runner.run()!"
                assert runner.run.call_args[0][0] == cmd

    class configuration_proxy:
        "Dict-like proxy for self.config"

        def setup_method(self):
            config = Config(defaults={"foo": "bar", "biz": {"baz": "boz"}})
            self.c = Context(config=config)

        def direct_access_allowed(self):
            assert self.c.config.__class__ == Config
            assert self.c.config["foo"] == "bar"
            assert self.c.config.foo == "bar"

        def config_attr_may_be_overwritten_at_runtime(self):
            new_config = Config(defaults={"foo": "notbar"})
            self.c.config = new_config
            assert self.c.foo == "notbar"

        def getitem(self):
            "___getitem__"
            assert self.c["foo"] == "bar"
            assert self.c["biz"]["baz"] == "boz"

        def getattr(self):
            "__getattr__"
            assert self.c.foo == "bar"
            assert self.c.biz.baz == "boz"

        def get(self):
            assert self.c.get("foo") == "bar"
            assert self.c.get("nope", "wut") == "wut"
            assert self.c.biz.get("nope", "hrm") == "hrm"

        def pop(self):
            assert self.c.pop("foo") == "bar"
            assert self.c.pop("foo", "notbar") == "notbar"
            assert self.c.biz.pop("baz") == "boz"

        def popitem(self):
            assert self.c.biz.popitem() == ("baz", "boz")
            del self.c["biz"]
            assert self.c.popitem() == ("foo", "bar")
            assert self.c.config == {}

        def del_(self):
            "del"
            del self.c["foo"]
            del self.c["biz"]["baz"]
            assert self.c.biz == {}
            del self.c["biz"]
            assert self.c.config == {}

        def clear(self):
            self.c.biz.clear()
            assert self.c.biz == {}
            self.c.clear()
            assert self.c.config == {}

        def setdefault(self):
            assert self.c.setdefault("foo") == "bar"
            assert self.c.biz.setdefault("baz") == "boz"
            assert self.c.setdefault("notfoo", "notbar") == "notbar"
            assert self.c.notfoo == "notbar"
            assert self.c.biz.setdefault("otherbaz", "otherboz") == "otherboz"
            assert self.c.biz.otherbaz == "otherboz"

        def update(self):
            self.c.update({"newkey": "newval"})
            assert self.c["newkey"] == "newval"
            assert self.c.foo == "bar"
            self.c.biz.update(otherbaz="otherboz")
            assert self.c.biz.otherbaz == "otherboz"

    class cwd:
        def setup_method(self):
            self.c = Context()

        def simple(self):
            self.c.command_cwds = ["a", "b"]
            assert self.c.cwd == os.path.join("a", "b")

        def nested_absolute_path(self):
            self.c.command_cwds = ["a", "/b", "c"]
            assert self.c.cwd == os.path.join("/b", "c")

        def multiple_absolute_paths(self):
            self.c.command_cwds = ["a", "/b", "c", "/d", "e"]
            assert self.c.cwd == os.path.join("/d", "e")

        def home(self):
            self.c.command_cwds = ["a", "~b", "c"]
            assert self.c.cwd == os.path.join("~b", "c")

    class cd:
        _escaped_prompt = re.escape(Config().sudo.prompt)

        @patch(local_path)
        def should_apply_to_run(self, Local):
            runner = Local.return_value
            c = Context()
            with c.cd("foo"):
                c.run("whoami")

            cmd = "cd foo && whoami"
            assert runner.run.called, "run() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def should_apply_to_sudo(self, Local):
            runner = Local.return_value
            c = Context()
            with c.cd("foo"):
                c.sudo("whoami")

            cmd = "sudo -S -p '[sudo] password: ' cd foo && whoami"
            assert runner.run.called, "sudo() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def should_occur_before_prefixes(self, Local):
            runner = Local.return_value
            c = Context()
            with c.prefix("source venv"):
                with c.cd("foo"):
                    c.run("whoami")

            cmd = "cd foo && source venv && whoami"
            assert runner.run.called, "run() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def should_use_finally_to_revert_changes_on_exceptions(self, Local):
            class Oops(Exception):
                pass

            runner = Local.return_value
            c = Context()
            try:
                with c.cd("foo"):
                    c.run("whoami")
                    assert runner.run.call_args[0][0] == "cd foo && whoami"
                    raise Oops
            except Oops:
                pass
            c.run("ls")
            # When bug present, this would be "cd foo && ls"
            assert runner.run.call_args[0][0] == "ls"

        @patch(local_path)
        def cd_should_accept_any_stringable_object(self, Local):
            class Path:
                def __init__(self, value):
                    self.value = value

                def __str__(self):
                    return self.value

            runner = Local.return_value
            c = Context()

            with c.cd(Path("foo")):
                c.run("whoami")

            cmd = "cd foo && whoami"
            assert runner.run.call_args[0][0] == cmd

    class prefix:
        @patch(local_path)
        def prefixes_should_apply_to_run(self, Local):
            runner = Local.return_value
            c = Context()
            with c.prefix("cd foo"):
                c.run("whoami")

            cmd = "cd foo && whoami"
            assert runner.run.called, "run() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def prefixes_should_apply_to_sudo(self, Local):
            runner = Local.return_value
            c = Context()
            with c.prefix("cd foo"):
                c.sudo("whoami")

            cmd = "sudo -S -p '[sudo] password: ' cd foo && whoami"
            assert runner.run.called, "sudo() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def nesting_should_retain_order(self, Local):
            runner = Local.return_value
            c = Context()
            with c.prefix("cd foo"):
                with c.prefix("cd bar"):
                    c.run("whoami")
                    cmd = "cd foo && cd bar && whoami"
                    assert (
                        runner.run.called
                    ), "run() never called runner.run()!"  # noqa
                    assert runner.run.call_args[0][0] == cmd

                c.run("whoami")
                cmd = "cd foo && whoami"
                assert runner.run.called, "run() never called runner.run()!"
                assert runner.run.call_args[0][0] == cmd

            # also test that prefixes do not persist
            c.run("whoami")
            cmd = "whoami"
            assert runner.run.called, "run() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def should_use_finally_to_revert_changes_on_exceptions(self, Local):
            class Oops(Exception):
                pass

            runner = Local.return_value
            c = Context()
            try:
                with c.prefix("cd foo"):
                    c.run("whoami")
                    assert runner.run.call_args[0][0] == "cd foo && whoami"
                    raise Oops
            except Oops:
                pass
            c.run("ls")
            # When bug present, this would be "cd foo && ls"
            assert runner.run.call_args[0][0] == "ls"

    class sudo:
        @patch(local_path)
        def prefixes_command_with_sudo(self, Local):
            runner = Local.return_value
            Context().sudo("whoami")
            # NOTE: implicitly tests default sudo.prompt conf value
            cmd = "sudo -S -p '[sudo] password: ' whoami"
            assert runner.run.called, "sudo() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def optional_user_argument_adds_u_and_H_flags(self, Local):
            runner = Local.return_value
            Context().sudo("whoami", user="rando")
            cmd = "sudo -S -p '[sudo] password: ' -H -u rando whoami"
            assert runner.run.called, "sudo() never called runner.run()!"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def honors_config_for_user_value(self, Local):
            runner = Local.return_value
            config = Config(overrides={"sudo": {"user": "rando"}})
            Context(config=config).sudo("whoami")
            cmd = "sudo -S -p '[sudo] password: ' -H -u rando whoami"
            assert runner.run.call_args[0][0] == cmd

        @patch(local_path)
        def user_kwarg_wins_over_config(self, Local):
            runner = Local.return_value
            config = Config(overrides={"sudo": {"user": "rando"}})
            Context(config=config).sudo("whoami", user="calrissian")
            cmd = "sudo -S -p '[sudo] password: ' -H -u calrissian whoami"
            assert runner.run.call_args[0][0] == cmd

        @trap
        @mock_subprocess()
        def echo_hides_extra_sudo_flags(self):
            skip()  # see TODO in sudo() re: clean output display
            config = Config(overrides={"runner": _Dummy})
            Context(config=config).sudo("nope", echo=True)
            output = sys.stdout.getvalue()
            sys.__stderr__.write(repr(output) + "\n")
            assert "-S" not in output
            assert Context().sudo.prompt not in output
            assert "sudo nope" in output

        @patch(local_path)
        def honors_config_for_prompt_value(self, Local):
            runner = Local.return_value
            config = Config(overrides={"sudo": {"prompt": "FEED ME: "}})
            Context(config=config).sudo("whoami")
            cmd = "sudo -S -p 'FEED ME: ' whoami"
            assert runner.run.call_args[0][0] == cmd

        def prompt_value_is_properly_shell_escaped(self):
            # I.e. setting it to "here's johnny!" doesn't explode.
            # NOTE: possibly best to tie into issue #2
            skip()

        @patch(local_path)
        def explicit_env_vars_are_preserved(self, Local):
            runner = Local.return_value
            Context().sudo(
                "whoami",
                env={"GRATUITOUS_ENVIRONMENT_VARIABLE": "arbitrary value"},
            )
            assert (
                "--preserve-env='GRATUITOUS_ENVIRONMENT_VARIABLE'"
                in runner.run.call_args[0][0]
            )

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
            context.sudo("whoami", **kwargs)
            # Tease out the interesting bits - pattern/response - ignoring the
            # sentinel, etc for now.
            prompt_responses = [
                (watcher.pattern, watcher.response)
                for watcher in runner.run.call_args[1]["watchers"]
            ]
            assert prompt_responses == expected

        def autoresponds_with_password_kwarg(self):
            # NOTE: technically duplicates the unitty test(s) in watcher tests.
            expected = [(_escaped_prompt, "secret\n")]
            self._expect_responses(expected, kwargs={"password": "secret"})

        def honors_configured_sudo_password(self):
            config = Config(overrides={"sudo": {"password": "secret"}})
            expected = [(_escaped_prompt, "secret\n")]
            self._expect_responses(expected, config=config)

        def sudo_password_kwarg_wins_over_config(self):
            config = Config(overrides={"sudo": {"password": "notsecret"}})
            kwargs = {"password": "secret"}
            expected = [(_escaped_prompt, "secret\n")]
            self._expect_responses(expected, config=config, kwargs=kwargs)

        class auto_response_merges_with_other_responses:
            def setup_method(self):
                class DummyWatcher(StreamWatcher):
                    def submit(self, stream):
                        pass

                self.watcher_klass = DummyWatcher

            @patch(local_path)
            def kwarg_only_adds_to_kwarg(self, Local):
                runner = Local.return_value
                context = Context()
                watcher = self.watcher_klass()
                context.sudo("whoami", watchers=[watcher])
                # When sudo() called w/ user-specified watchers, we add ours to
                # that list
                watchers = runner.run.call_args[1]["watchers"]
                # Will raise ValueError if not in the list
                watchers.remove(watcher)
                # Only remaining item in list should be our sudo responder
                assert len(watchers) == 1
                assert isinstance(watchers[0], FailingResponder)
                assert watchers[0].pattern == _escaped_prompt

            @patch(local_path)
            def config_only(self, Local):
                runner = Local.return_value
                # Set a config-driven list of watchers
                watcher = self.watcher_klass()
                overrides = {"run": {"watchers": [watcher]}}
                config = Config(overrides=overrides)
                Context(config=config).sudo("whoami")
                # Expect that sudo() extracted that config value & put it into
                # the kwarg level. (See comment in sudo() about why...)
                watchers = runner.run.call_args[1]["watchers"]
                # Will raise ValueError if not in the list
                watchers.remove(watcher)
                # Only remaining item in list should be our sudo responder
                assert len(watchers) == 1
                assert isinstance(watchers[0], FailingResponder)
                assert watchers[0].pattern == _escaped_prompt

            @patch(local_path)
            def config_use_does_not_modify_config(self, Local):
                runner = Local.return_value
                watcher = self.watcher_klass()
                overrides = {"run": {"watchers": [watcher]}}
                config = Config(overrides=overrides)
                Context(config=config).sudo("whoami")
                # Here, 'watchers' is _the same object_ as was passed into
                # run(watchers=...).
                watchers = runner.run.call_args[1]["watchers"]
                # We want to make sure that what's in the config we just
                # generated, is untouched by the manipulation done inside
                # sudo().
                # First, that they aren't the same obj
                err = "Found sudo() reusing config watchers list directly!"
                assert watchers is not config.run.watchers, err
                # And that the list is as it was before (i.e. it is not both
                # our watcher and the sudo()-added one)
                err = "Our config watchers list was modified!"
                assert config.run.watchers == [watcher], err

            @patch(local_path)
            def both_kwarg_and_config(self, Local):
                runner = Local.return_value
                # Set a config-driven list of watchers
                conf_watcher = self.watcher_klass()
                overrides = {"run": {"watchers": [conf_watcher]}}
                config = Config(overrides=overrides)
                # AND supply a DIFFERENT kwarg-driven list of watchers
                kwarg_watcher = self.watcher_klass()
                Context(config=config).sudo("whoami", watchers=[kwarg_watcher])
                # Expect that the kwarg watcher and our internal one were the
                # final result.
                watchers = runner.run.call_args[1]["watchers"]
                # Will raise ValueError if not in the list. .remove() uses
                # identity testing, so two instances of self.watcher_klass will
                # be different values here.
                watchers.remove(kwarg_watcher)
                # Only remaining item in list should be our sudo responder
                assert len(watchers) == 1
                assert conf_watcher not in watchers  # Extra sanity
                assert isinstance(watchers[0], FailingResponder)
                assert watchers[0].pattern == _escaped_prompt

        @patch(local_path)
        def passes_through_other_run_kwargs(self, Local):
            runner = Local.return_value
            Context().sudo(
                "whoami", echo=True, warn=False, hide=True, encoding="ascii"
            )
            assert runner.run.called, "sudo() never called runner.run()!"
            kwargs = runner.run.call_args[1]
            assert kwargs["echo"] is True
            assert kwargs["warn"] is False
            assert kwargs["hide"] is True
            assert kwargs["encoding"] == "ascii"

        @patch(local_path)
        def returns_run_result(self, Local):
            runner = Local.return_value
            expected = runner.run.return_value
            result = Context().sudo("whoami")
            err = "sudo() did not return run()'s return value!"
            assert result is expected, err

        @mock_subprocess(out="something", exit=None)
        def raises_auth_failure_when_failure_detected(self):
            with patch("invoke.context.FailingResponder") as klass:
                unacceptable = Mock(side_effect=ResponseNotAccepted)
                klass.return_value.submit = unacceptable
                excepted = False
                try:
                    config = Config(overrides={"sudo": {"password": "nope"}})
                    Context(config=config).sudo("meh", hide=True)
                except AuthFailure as e:
                    # Basic sanity checks; most of this is really tested in
                    # Runner tests.
                    assert e.result.exited is None
                    expected = "The password submitted to prompt '[sudo] password: ' was rejected."  # noqa
                    assert str(e) == expected
                    excepted = True
                # Can't use except/else as that masks other real exceptions,
                # such as incorrectly unhandled ThreadErrors
                if not excepted:
                    assert False, "Did not raise AuthFailure!"

    def can_be_pickled(self):
        c = Context()
        c.foo = {"bar": {"biz": ["baz", "buzz"]}}
        c2 = pickle.loads(pickle.dumps(c))
        assert c == c2
        assert c is not c2
        assert c.foo.bar.biz is not c2.foo.bar.biz


class MockContext_:
    def init_still_acts_like_superclass_init(self):
        # No required args
        assert isinstance(MockContext().config, Config)
        config = Config(overrides={"foo": "bar"})
        # Posarg
        assert MockContext(config).config is config
        # Kwarg
        assert MockContext(config=config).config is config

    def non_config_init_kwargs_used_as_return_values_for_methods(self):
        c = MockContext(run=Result("some output"))
        assert c.run("doesn't mattress").stdout == "some output"

    def return_value_kwargs_can_take_iterables_too(self):
        c = MockContext(run=(Result("some output"), Result("more!")))
        assert c.run("doesn't mattress").stdout == "some output"
        assert c.run("still doesn't mattress").stdout == "more!"

    def return_value_kwargs_may_be_command_string_maps(self):
        c = MockContext(run={"foo": Result("bar")})
        assert c.run("foo").stdout == "bar"

    def return_value_map_kwargs_may_take_iterables_too(self):
        c = MockContext(run={"foo": (Result("bar"), Result("biz"))})
        assert c.run("foo").stdout == "bar"
        assert c.run("foo").stdout == "biz"

    def regexen_return_value_map_keys_match_on_command(self):
        c = MockContext(
            run={"string": Result("yup"), re.compile(r"foo.*"): Result("bar")}
        )
        assert c.run("string").stdout == "yup"
        assert c.run("foobar").stdout == "bar"

    class boolean_result_shorthand:
        def as_singleton_args(self):
            assert MockContext(run=True).run("anything").ok
            assert not MockContext(run=False).run("anything", warn=True).ok

        def as_iterables(self):
            mc = MockContext(run=[True, False])
            assert mc.run("anything").ok
            assert not mc.run("anything", warn=True).ok

        def as_dict_values(self):
            mc = MockContext(run=dict(foo=True, bar=False))
            assert mc.run("foo").ok
            assert not mc.run("bar", warn=True).ok

    class string_result_shorthand:
        def as_singleton_args(self):
            assert MockContext(run="foo").run("anything").stdout == "foo"

        def as_iterables(self):
            mc = MockContext(run=["definition", "of", "insanity"])
            assert mc.run("anything").stdout == "definition"
            assert mc.run("anything").stdout == "of"
            assert mc.run("anything").stdout == "insanity"

        def as_dict_values(self):
            mc = MockContext(run=dict(foo="foo", bar="bar"))
            assert mc.run("foo").stdout == "foo"
            assert mc.run("bar").stdout == "bar"

    class commands_injected_into_Result:
        @mark.parametrize(
            "kwargs", (dict(), dict(command=""), dict(command=None))
        )
        def when_not_set_or_falsey(self, kwargs):
            c = MockContext(run={"foo": Result("bar", **kwargs)})
            assert c.run("foo").command == "foo"

        def does_not_occur_when_truthy(self):
            # Not sure why you'd want this but whatevs!
            c = MockContext(run={"foo": Result("bar", command="nope")})
            assert c.run("foo").command == "nope"  # not "bar"

    def methods_with_no_kwarg_values_raise_NotImplementedError(self):
        with raises(NotImplementedError):
            MockContext().run("onoz I did not anticipate this would happen")

    def does_not_consume_results_by_default(self):
        mc = MockContext(
            run=dict(
                singleton=True,  # will repeat
                wassup=Result("yo"),  # ditto
                iterable=[Result("tick"), Result("tock")],  # will not
            ),
        )
        assert mc.run("singleton").ok
        assert mc.run("singleton").ok  # not consumed
        assert mc.run("wassup").ok
        assert mc.run("wassup").ok  # not consumed
        assert mc.run("iterable").stdout == "tick"
        assert mc.run("iterable").stdout == "tock"
        assert mc.run("iterable").stdout == "tick"  # not consumed
        assert mc.run("iterable").stdout == "tock"

    def consumes_singleton_results_when_repeat_False(self):
        mc = MockContext(
            repeat=False,
            run=dict(
                singleton=True,
                wassup=Result("yo"),
                iterable=[Result("tick"), Result("tock")],
            ),
        )
        assert mc.run("singleton").ok
        with raises(NotImplementedError):  # was consumed
            mc.run("singleton")
        assert mc.run("wassup").ok
        with raises(NotImplementedError):  # was consumed
            mc.run("wassup")
        assert mc.run("iterable").stdout == "tick"
        assert mc.run("iterable").stdout == "tock"
        with raises(NotImplementedError):  # was consumed
            assert mc.run("iterable")

    def sudo_also_covered(self):
        c = MockContext(sudo=Result(stderr="super duper"))
        assert c.sudo("doesn't mattress").stderr == "super duper"
        try:
            MockContext().sudo("meh")
        except NotImplementedError as e:
            assert str(e) == "meh"
        else:
            assert False, "Did not get a NotImplementedError for sudo!"

    class exhausted_nonrepeating_return_values_also_raise_NotImplementedError:
        def _expect_NotImplementedError(self, context):
            context.run("something")
            try:
                context.run("something")
            except NotImplementedError as e:
                assert str(e) == "something"
            else:
                assert False, "Didn't raise NotImplementedError"

        def single_value(self):
            self._expect_NotImplementedError(
                MockContext(run=Result("meh"), repeat=False)
            )

        def iterable(self):
            self._expect_NotImplementedError(
                MockContext(run=[Result("meh")], repeat=False)
            )

        def mapping_to_single_value(self):
            self._expect_NotImplementedError(
                MockContext(run={"something": Result("meh")}, repeat=False)
            )

        def mapping_to_iterable(self):
            self._expect_NotImplementedError(
                MockContext(run={"something": [Result("meh")]}, repeat=False)
            )

    def unexpected_kwarg_type_yields_TypeError(self):
        with raises(TypeError):
            MockContext(run=123)

    class can_modify_return_value_maps_after_instantiation:
        class non_dict_type_instantiation_values_yield_TypeErrors:
            class no_stored_result:
                def run(self):
                    mc = MockContext()
                    with raises(TypeError):
                        mc.set_result_for("run", "whatever", Result("bar"))

                def sudo(self):
                    mc = MockContext()
                    with raises(TypeError):
                        mc.set_result_for("sudo", "whatever", Result("bar"))

            class single_result:
                def run(self):
                    mc = MockContext(run=Result("foo"))
                    with raises(TypeError):
                        mc.set_result_for("run", "whatever", Result("bar"))

                def sudo(self):
                    mc = MockContext(sudo=Result("foo"))
                    with raises(TypeError):
                        mc.set_result_for("sudo", "whatever", Result("bar"))

            class iterable_result:
                def run(self):
                    mc = MockContext(run=[Result("foo")])
                    with raises(TypeError):
                        mc.set_result_for("run", "whatever", Result("bar"))

                def sudo(self):
                    mc = MockContext(sudo=[Result("foo")])
                    with raises(TypeError):
                        mc.set_result_for("sudo", "whatever", Result("bar"))

        def run(self):
            mc = MockContext(run={"foo": Result("bar")})
            assert mc.run("foo").stdout == "bar"
            mc.set_result_for("run", "foo", Result("biz"))
            assert mc.run("foo").stdout == "biz"

        def sudo(self):
            mc = MockContext(sudo={"foo": Result("bar")})
            assert mc.sudo("foo").stdout == "bar"
            mc.set_result_for("sudo", "foo", Result("biz"))
            assert mc.sudo("foo").stdout == "biz"

    def wraps_run_and_sudo_with_Mock(self, clean_sys_modules):
        sys.modules["mock"] = None  # legacy
        sys.modules["unittest.mock"] = Mock(Mock=Mock)  # buffalo buffalo
        mc = MockContext(
            run={"foo": Result("bar")}, sudo={"foo": Result("bar")}
        )
        assert isinstance(mc.run, Mock)
        assert isinstance(mc.sudo, Mock)
