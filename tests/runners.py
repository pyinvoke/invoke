import os
import struct
import sys
import types
from io import BytesIO
from itertools import chain, repeat

from invoke.vendor.six import StringIO, b, PY2, iteritems

from spec import (
    Spec, trap, eq_, skip, ok_, raises, assert_contains, assert_not_contains
)
from mock import patch, Mock, call

from invoke import (
    Runner, Local, Context, Config, Failure, ThreadException, Responder,
    WatcherError, UnexpectedExit, StreamWatcher, Result,
)
from invoke.platform import WINDOWS

from _util import (
    mock_subprocess, mock_pty, skip_if_windows, _Dummy,
    _KeyboardInterruptingRunner, OhNoz, _,
)


class RaisingWatcher(StreamWatcher):
    def submit(self, stream):
        raise WatcherError("meh")


def _run(*args, **kwargs):
    klass = kwargs.pop('klass', _Dummy)
    settings = kwargs.pop('settings', {})
    context = Context(config=Config(overrides=settings))
    return klass(context).run(*args, **kwargs)

def _runner(out='', err='', **kwargs):
    klass = kwargs.pop('klass', _Dummy)
    runner = klass(Context(config=Config(overrides=kwargs)))
    if 'exits' in kwargs:
        runner.returncode = Mock(return_value=kwargs.pop('exits'))
    out_file = BytesIO(b(out))
    err_file = BytesIO(b(err))
    runner.read_proc_stdout = out_file.read
    runner.read_proc_stderr = err_file.read
    return runner


class Runner_(Spec):
    # NOTE: these copies of _run and _runner form the base case of "test Runner
    # subclasses via self._run/_runner helpers" functionality. See how e.g.
    # Local_ uses the same approach but bakes in the dummy class used.
    def _run(self, *args, **kwargs):
        return _run(*args, **kwargs)

    def _runner(self, *args, **kwargs):
        return _runner(*args, **kwargs)

    def _mock_stdin_writer(self):
        """
        Return new _Dummy subclass whose write_proc_stdin() method is a mock.
        """
        class MockedStdin(_Dummy):
            pass
        MockedStdin.write_proc_stdin = Mock()
        return MockedStdin


    class init:
        "__init__"
        def takes_a_context_instance(self):
            c = Context()
            eq_(Runner(c).context, c)

        @raises(TypeError)
        def context_instance_is_required(self):
            Runner()

    class run:
        def handles_invalid_kwargs_like_any_other_function(self):
            try:
                self._run(_, nope_noway_nohow='as if')
            except TypeError as e:
                ok_('got an unexpected keyword argument' in str(e))
            else:
                assert False, "Invalid run() kwarg didn't raise TypeError"

    class warn:
        def honors_config(self):
            runner = self._runner(run={'warn': True}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run(_)

        def kwarg_beats_config(self):
            runner = self._runner(run={'warn': False}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run(_, warn=True)

        def does_not_apply_to_watcher_errors(self):
            runner = self._runner(out="stuff")
            try:
                watcher = RaisingWatcher()
                runner.run(_, watchers=[watcher], warn=True, hide=True)
            except Failure as e:
                ok_(isinstance(e.reason, WatcherError))
            else:
                assert False, "Did not raise Failure for WatcherError!"

    class hide:
        @trap
        def honors_config(self):
            runner = self._runner(out='stuff', run={'hide': True})
            r = runner.run(_)
            eq_(r.stdout, 'stuff')
            eq_(sys.stdout.getvalue(), '')

        @trap
        def kwarg_beats_config(self):
            runner = self._runner(out='stuff')
            r = runner.run(_, hide=True)
            eq_(r.stdout, 'stuff')
            eq_(sys.stdout.getvalue(), '')

    class pty:
        def pty_defaults_to_off(self):
            eq_(self._run(_).pty, False)

        def honors_config(self):
            runner = self._runner(run={'pty': True})
            eq_(runner.run(_).pty, True)

        def kwarg_beats_config(self):
            runner = self._runner(run={'pty': False})
            eq_(runner.run(_, pty=True).pty, True)

    class shell:
        def defaults_to_bash_when_pty_True(self):
            eq_(self._run(_, pty=True).shell, '/bin/bash')

        def defaults_to_bash_when_pty_False(self):
            eq_(self._run(_, pty=False).shell, '/bin/bash')

        def may_be_overridden(self):
            eq_(self._run(_, shell='/bin/zsh').shell, '/bin/zsh')

        def may_be_configured(self):
            runner = self._runner(run={'shell': '/bin/tcsh'})
            eq_(runner.run(_).shell, '/bin/tcsh')

        def kwarg_beats_config(self):
            runner = self._runner(run={'shell': '/bin/tcsh'})
            eq_(runner.run(_, shell='/bin/zsh').shell, '/bin/zsh')

    class env:
        def defaults_to_os_environ(self):
            eq_(self._run(_).env, os.environ)

        def updates_when_dict_given(self):
            expected = dict(os.environ, FOO='BAR')
            eq_(self._run(_, env={'FOO': 'BAR'}).env, expected)

        def replaces_when_replace_env_True(self):
            eq_(
                self._run(_, env={'JUST': 'ME'}, replace_env=True).env,
                {'JUST': 'ME'}
            )

        def config_can_be_used(self):
            eq_(
                self._run(_, settings={'run': {'env': {'FOO': 'BAR'}}}).env,
                dict(os.environ, FOO='BAR'),
            )

        def kwarg_wins_over_config(self):
            settings = {'run': {'env': {'FOO': 'BAR'}}}
            kwarg = {'FOO': 'NOTBAR'}
            eq_(
                self._run(_, settings=settings, env=kwarg).env['FOO'],
                'NOTBAR'
            )

    class return_value:
        def return_code(self):
            """
            Result has .return_code (and .exited) containing exit code int
            """
            runner = self._runner(exits=17)
            r = runner.run(_, warn=True)
            eq_(r.return_code, 17)
            eq_(r.exited, 17)

        def ok_attr_indicates_success(self):
            runner = self._runner()
            eq_(runner.run(_).ok, True) # default dummy retval is 0

        def ok_attr_indicates_failure(self):
            runner = self._runner(exits=1)
            eq_(runner.run(_, warn=True).ok, False)

        def failed_attr_indicates_success(self):
            runner = self._runner()
            eq_(runner.run(_).failed, False) # default dummy retval is 0

        def failed_attr_indicates_failure(self):
            runner = self._runner(exits=1)
            eq_(runner.run(_, warn=True).failed, True)

        @trap
        def stdout_attribute_contains_stdout(self):
            runner = self._runner(out='foo')
            eq_(runner.run(_).stdout, "foo")
            eq_(sys.stdout.getvalue(), "foo")

        @trap
        def stderr_attribute_contains_stderr(self):
            runner = self._runner(err='foo')
            eq_(runner.run(_).stderr, "foo")
            eq_(sys.stderr.getvalue(), "foo")

        def whether_pty_was_used(self):
            eq_(self._run(_).pty, False)
            eq_(self._run(_, pty=True).pty, True)

        def command_executed(self):
            eq_(self._run(_).command, _)

        def shell_used(self):
            eq_(self._run(_).shell, '/bin/bash')

        def hide_param_exposed_and_normalized(self):
            eq_(self._run(_, hide=True).hide, ('stdout', 'stderr'))
            eq_(self._run(_, hide=False).hide, tuple())
            eq_(self._run(_, hide='stderr').hide, ('stderr',))

    class command_echoing:
        @trap
        def off_by_default(self):
            self._run("my command")
            eq_(sys.stdout.getvalue(), "")

        @trap
        def enabled_via_kwarg(self):
            self._run("my command", echo=True)
            assert_contains(sys.stdout.getvalue(), "my command")

        @trap
        def enabled_via_config(self):
            self._run("yup", settings={'run': {'echo': True}})
            assert_contains(sys.stdout.getvalue(), "yup")

        @trap
        def kwarg_beats_config(self):
            self._run("yup", echo=True, settings={'run': {'echo': False}})
            assert_contains(sys.stdout.getvalue(), "yup")

        @trap
        def uses_ansi_bold(self):
            self._run("my command", echo=True)
            # TODO: vendor & use a color module
            eq_(sys.stdout.getvalue(), "\x1b[1;37mmy command\x1b[0m\n")

    class encoding:
        # NOTE: these tests just check what Runner.encoding ends up as; it's
        # difficult/impossible to mock string objects themselves to see what
        # .decode() is being given :(
        #
        # TODO: consider using truly "nonstandard"-encoded byte sequences as
        # fixtures, encoded with something that isn't compatible with UTF-8
        # (UTF-7 kinda is, so...) so we can assert that the decoded string is
        # equal to its Unicode equivalent.
        #
        # Use UTF-7 as a valid encoding unlikely to be a real default derived
        # from test-runner's locale.getpreferredencoding()
        def defaults_to_encoding_method_result(self):
            # Setup
            runner = self._runner()
            encoding = 'UTF-7'
            runner.default_encoding = Mock(return_value=encoding)
            # Execution & assertion
            runner.run(_)
            runner.default_encoding.assert_called_with()
            eq_(runner.encoding, 'UTF-7')

        def honors_config(self):
            c = Context(Config(overrides={'run': {'encoding': 'UTF-7'}}))
            runner = _Dummy(c)
            runner.default_encoding = Mock(return_value='UTF-not-7')
            runner.run(_)
            eq_(runner.encoding, 'UTF-7')

        def honors_kwarg(self):
            skip()

        def uses_locale_module_for_default_encoding(self):
            # Actually testing this highly OS/env specific stuff is very
            # error-prone; so we degrade to just testing expected function
            # calls for now :(
            with patch('invoke.runners.locale') as fake_locale:
                fake_locale.getdefaultlocale.return_value = ('meh', 'UHF-8')
                fake_locale.getpreferredencoding.return_value = 'FALLBACK'
                expected = 'UHF-8' if (PY2 and not WINDOWS) else 'FALLBACK'
                eq_(self._runner().default_encoding(), expected)

        def falls_back_to_defaultlocale_when_preferredencoding_is_None(self):
            if PY2:
                skip()
            with patch('invoke.runners.locale') as fake_locale:
                fake_locale.getdefaultlocale.return_value = (None, None)
                fake_locale.getpreferredencoding.return_value = 'FALLBACK'
                eq_(self._runner().default_encoding(), 'FALLBACK')

    class output_hiding:
        @trap
        def _expect_hidden(self, hide, expect_out="", expect_err=""):
            self._runner(out='foo', err='bar').run(_, hide=hide)
            eq_(sys.stdout.getvalue(), expect_out)
            eq_(sys.stderr.getvalue(), expect_err)

        def both_hides_everything(self):
            self._expect_hidden('both')

        def True_hides_everything(self):
            self._expect_hidden(True)

        def out_only_hides_stdout(self):
            self._expect_hidden('out', expect_out="", expect_err="bar")

        def err_only_hides_stderr(self):
            self._expect_hidden('err', expect_out="foo", expect_err="")

        def accepts_stdout_alias_for_out(self):
            self._expect_hidden('stdout', expect_out="", expect_err="bar")

        def accepts_stderr_alias_for_err(self):
            self._expect_hidden('stderr', expect_out="foo", expect_err="")

        def None_hides_nothing(self):
            self._expect_hidden(None, expect_out="foo", expect_err="bar")

        def False_hides_nothing(self):
            self._expect_hidden(False, expect_out="foo", expect_err="bar")

        @raises(ValueError)
        def unknown_vals_raises_ValueError(self):
            self._run(_, hide="wat?")

        def unknown_vals_mention_value_given_in_error(self):
            value = "penguinmints"
            try:
                self._run(_, hide=value)
            except ValueError as e:
                msg = "Error from run(hide=xxx) did not tell user what the bad value was!" # noqa
                msg += "\nException msg: {0}".format(e)
                ok_(value in str(e), msg)
            else:
                assert False, "run() did not raise ValueError for bad hide= value" # noqa

        def does_not_affect_capturing(self):
            eq_(self._runner(out='foo').run(_, hide=True).stdout, 'foo')

        @trap
        def overrides_echoing(self):
            self._runner().run('invisible', hide=True, echo=True)
            assert_not_contains(sys.stdout.getvalue(), 'invisible')

    class output_stream_overrides:
        @trap
        def out_defaults_to_sys_stdout(self):
            "out_stream defaults to sys.stdout"
            self._runner(out="sup").run(_)
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        def err_defaults_to_sys_stderr(self):
            "err_stream defaults to sys.stderr"
            self._runner(err="sup").run(_)
            eq_(sys.stderr.getvalue(), "sup")

        @trap
        def out_can_be_overridden(self):
            "out_stream can be overridden"
            out = StringIO()
            self._runner(out="sup").run(_, out_stream=out)
            eq_(out.getvalue(), "sup")
            eq_(sys.stdout.getvalue(), "")

        @trap
        def err_can_be_overridden(self):
            "err_stream can be overridden"
            err = StringIO()
            self._runner(err="sup").run(_, err_stream=err)
            eq_(err.getvalue(), "sup")
            eq_(sys.stderr.getvalue(), "")

        @trap
        def pty_defaults_to_sys(self):
            self._runner(out="sup").run(_, pty=True)
            eq_(sys.stdout.getvalue(), "sup")

        @trap
        def pty_out_can_be_overridden(self):
            out = StringIO()
            self._runner(out="yo").run(_, pty=True, out_stream=out)
            eq_(out.getvalue(), "yo")
            eq_(sys.stdout.getvalue(), "")

    class output_stream_handling:
        # Mostly corner cases, generic behavior's covered above
        def writes_and_flushes_to_stdout(self):
            out = Mock(spec=StringIO)
            self._runner(out="meh").run(_, out_stream=out)
            out.write.assert_called_once_with("meh")
            out.flush.assert_called_once_with()

        def writes_and_flushes_to_stderr(self):
            err = Mock(spec=StringIO)
            self._runner(err="whatever").run(_, err_stream=err)
            err.write.assert_called_once_with("whatever")
            err.flush.assert_called_once_with()

    class input_stream_handling:
        # NOTE: actual autoresponder tests are elsewhere. These just test that
        # stdin works normally & can be overridden.
        @patch('invoke.runners.sys.stdin', StringIO("Text!"))
        def defaults_to_sys_stdin(self):
            # Execute w/ runner class that has a mocked stdin_writer
            klass = self._mock_stdin_writer()
            self._runner(klass=klass).run(_, out_stream=StringIO())
            # Check that mocked writer was called w/ the data from our patched
            # sys.stdin.
            # NOTE: this also tests that non-fileno-bearing streams read/write
            # 1 byte at a time. See farther-down test for fileno-bearing stdin
            calls = list(map(lambda x: call(x), "Text!"))
            klass.write_proc_stdin.assert_has_calls(calls, any_order=False)

        def can_be_overridden(self):
            klass = self._mock_stdin_writer()
            in_stream = StringIO("Hey, listen!")
            self._runner(klass=klass).run(
                _,
                in_stream=in_stream,
                out_stream=StringIO(),
            )
            # stdin mirroring occurs char-by-char
            calls = list(map(lambda x: call(x), "Hey, listen!"))
            klass.write_proc_stdin.assert_has_calls(calls, any_order=False)

        @patch('invoke.util.debug')
        def exceptions_get_logged(self, mock_debug):
            # Make write_proc_stdin asplode
            klass = self._mock_stdin_writer()
            klass.write_proc_stdin.side_effect = OhNoz("oh god why")
            # Execute with some stdin to trigger that asplode (but skip the
            # actual bubbled-up raising of it so we can check things out)
            try:
                stdin = StringIO("non-empty")
                self._runner(klass=klass).run(_, in_stream=stdin)
            except ThreadException:
                pass
            # Assert debug() was called w/ expected format
            # TODO: make the debug call a method on ExceptionHandlingThread,
            # then make thread class configurable somewhere in Runner, and pass
            # in a customized ExceptionHandlingThread that has a Mock for that
            # method?
            mock_debug.assert_called_with("Encountered exception OhNoz('oh god why',) in thread for 'handle_stdin'") # noqa

    class failure_handling:
        @raises(UnexpectedExit)
        def fast_failures(self):
            self._runner(exits=1).run(_)

        def non_1_return_codes_still_act_as_failure(self):
            r = self._runner(exits=17).run(_, warn=True)
            eq_(r.failed, True)

        class UnexpectedExit_repr:
            def similar_to_just_the_result_repr(self):
                try:
                    self._runner(exits=23).run(_)
                except UnexpectedExit as e:
                    expected = "<UnexpectedExit: cmd='{0}' exited=23>"
                    eq_(
                        repr(e),
                        expected.format(_),
                    )

        class UnexpectedExit_str:
            def setup(self):
                def lines(prefix):
                    return "\n".join(
                        "{0} {1}".format(prefix, x) for x in range(1, 26)
                    ) + "\n"
                self._stdout = lines('stdout')
                self._stderr = lines('stderr')

            @trap
            def displays_command_and_exit_code_by_default(self):
                try:
                    self._runner(
                        exits=23,
                        out=self._stdout,
                        err=self._stderr,
                    ).run(_)
                except UnexpectedExit as e:
                    eq_(str(e), """Encountered a bad command exit code!

Command: '{0}'

Exit code: 23

Stdout: already printed

Stderr: already printed

""".format(_))
                else:
                    assert False, "Failed to raise UnexpectedExit!"

            @trap
            def does_not_display_stderr_when_pty_True(self):
                try:
                    self._runner(
                        exits=13, out=self._stdout, err=self._stderr
                    ).run(_, pty=True)
                except UnexpectedExit as e:
                    eq_(str(e), """Encountered a bad command exit code!

Command: '{0}'

Exit code: 13

Stdout: already printed

Stderr: n/a (PTYs have no stderr)

""".format(_))

            @trap
            def pty_stderr_message_wins_over_hidden_stderr(self):
                try:
                    self._runner(
                        exits=1, out=self._stdout, err=self._stderr
                    ).run(_, pty=True, hide=True)
                except UnexpectedExit as e:
                    r = str(e)
                    ok_("Stderr: n/a (PTYs have no stderr)" in r)
                    ok_("Stderr: already printed" not in r)

            @trap
            def explicit_hidden_stream_tail_display(self):
                # All the permutations of what's displayed when, are in
                # subsequent test, which does 'x in y' assertions; this one
                # here ensures the actual format of the display (newlines, etc)
                # is as desired.
                try:
                    self._runner(
                        exits=77, out=self._stdout, err=self._stderr
                    ).run(_, hide=True)
                except UnexpectedExit as e:
                    eq_(str(e), """Encountered a bad command exit code!

Command: '{0}'

Exit code: 77

Stdout:

stdout 16
stdout 17
stdout 18
stdout 19
stdout 20
stdout 21
stdout 22
stdout 23
stdout 24
stdout 25

Stderr:

stderr 16
stderr 17
stderr 18
stderr 19
stderr 20
stderr 21
stderr 22
stderr 23
stderr 24
stderr 25

""".format(_))

            @trap
            def displays_tails_of_streams_only_when_hidden(self):
                def oops(msg, r, hide):
                    return "{0}! hide={1}; str output:\n\n{2}".format(
                        msg, hide, r
                    )
                for hide, expect_out, expect_err in (
                    (False, False, False),
                    (True, True, True),
                    ('stdout', True, False),
                    ('stderr', False, True),
                    ('both', True, True),
                ):
                    try:
                        self._runner(
                            exits=1, out=self._stdout, err=self._stderr
                        ).run(_, hide=hide)
                    except UnexpectedExit as e:
                        r = str(e)
                        # Expect that the top of output is never displayed
                        ok_(
                            "stdout 15" not in r,
                            oops("Too much stdout found", r, hide)
                        )
                        ok_(
                            "stderr 15" not in r,
                            oops("Too much stderr found", r, hide)
                        )
                        # Expect to see tail of stdout if we expected it
                        if expect_out:
                            ok_(
                                "stdout 16" in r,
                                oops("Didn't see stdout", r, hide)
                            )
                        # Expect to see tail of stderr if we expected it
                        if expect_err:
                            ok_(
                                "stderr 16" in r,
                                oops("Didn't see stderr", r, hide)
                            )
                    else:
                        assert False, "Failed to raise UnexpectedExit!"

        def _regular_error(self):
            self._runner(exits=1).run(_)

        def _watcher_error(self):
            klass = self._mock_stdin_writer()
            # Exited=None because real procs will have no useful .returncode()
            # result if they're aborted partway via an exception.
            runner = self._runner(klass=klass, out="stuff", exits=None)
            runner.run(_, watchers=[RaisingWatcher()], hide=True)

        # TODO: may eventually turn into having Runner raise distinct Failure
        # subclasses itself, at which point `reason` would probably go away.
        class reason:
            def is_None_for_regular_nonzero_exits(self):
                try:
                    self._regular_error()
                except Failure as e:
                    eq_(e.reason, None)
                else:
                    assert False, "Failed to raise Failure!"

            def is_None_for_custom_command_exits(self):
                # TODO: when we implement 'exitcodes 1 and 2 are actually OK'
                skip()

            def is_exception_when_WatcherError_raised_internally(self):
                try:
                    self._watcher_error()
                except Failure as e:
                    ok_(isinstance(e.reason, WatcherError))
                else:
                    assert False, "Failed to raise Failure!"

        # TODO: should these move elsewhere, eg to Result specific test file?
        # TODO: *is* there a nice way to split into multiple Response and/or
        # Failure subclasses? Given the split between "returned as a value when
        # no problem" and "raised as/attached to an exception when problem",
        # possibly not - complicates how the APIs need to be adhered to.
        class wrapped_result:
            def most_attrs_are_always_present(self):
                attrs = (
                    'command', 'shell', 'env', 'stdout', 'stderr', 'pty',
                )
                for method in (self._regular_error, self._watcher_error):
                    try:
                        method()
                    except Failure as e:
                        for attr in attrs:
                            ok_(getattr(e.result, attr) is not None)
                    else:
                        assert False, "Did not raise Failure!"

            class shell_exit_failure:
                def exited_is_integer(self):
                    try:
                        self._regular_error()
                    except Failure as e:
                        ok_(isinstance(e.result.exited, int))
                    else:
                        assert False, "Did not raise Failure!"

                def ok_bool_etc_are_falsey(self):
                    try:
                        self._regular_error()
                    except Failure as e:
                        eq_(e.result.ok, False)
                        eq_(e.result.failed, True)
                        ok_(not bool(e.result))
                        ok_(not e.result)
                    else:
                        assert False, "Did not raise Failure!"

                def stringrep_notes_exit_status(self):
                    try:
                        self._regular_error()
                    except Failure as e:
                        ok_("exited with status 1" in str(e.result))
                    else:
                        assert False, "Did not raise Failure!"

            class watcher_failure:
                def exited_is_None(self):
                    try:
                        self._watcher_error()
                    except Failure as e:
                        exited = e.result.exited
                        err = "Expected None, got {0!r}".format(exited)
                        ok_(exited is None, err)

                def ok_and_bool_still_are_falsey(self):
                    try:
                        self._watcher_error()
                    except Failure as e:
                        eq_(e.result.ok, False)
                        eq_(e.result.failed, True)
                        ok_(not bool(e.result))
                        ok_(not e.result)
                    else:
                        assert False, "Did not raise Failure!"

                def stringrep_lacks_exit_status(self):
                    try:
                        self._watcher_error()
                    except Failure as e:
                        ok_("exited with status" not in str(e.result))
                        expected = "not fully executed due to watcher error"
                        ok_(expected in str(e.result))
                    else:
                        assert False, "Did not raise Failure!"

    class threading:
        # NOTE: see also the more generic tests in concurrency.py
        def errors_within_io_thread_body_bubble_up(self):
            class Oops(_Dummy):
                def handle_stdout(self, **kwargs):
                    raise OhNoz()
                def handle_stderr(self, **kwargs):
                    raise OhNoz()

            runner = Oops(Context())
            try:
                runner.run("nah")
            except ThreadException as e:
                # Expect two separate OhNoz objects on 'e'
                eq_(len(e.exceptions), 2)
                for tup in e.exceptions:
                    ok_(isinstance(tup.value, OhNoz))
                    ok_(isinstance(tup.traceback, types.TracebackType))
                    eq_(tup.type, OhNoz)
                # TODO: test the arguments part of the tuple too. It's pretty
                # implementation-specific, though, so possibly not worthwhile.
            else:
                assert False, "Did not raise ThreadException as expected!"

        def io_thread_errors_str_has_details(self):
            class Oops(_Dummy):
                def handle_stdout(self, **kwargs):
                    raise OhNoz()
            runner = Oops(Context())
            try:
                runner.run("nah")
            except ThreadException as e:
                message = str(e)
                # Just make sure salient bits appear present, vs e.g. default
                # representation happening instead.
                ok_("Saw 1 exceptions within threads" in message)
                ok_("{'kwargs': " in message)
                ok_("Traceback (most recent call last):\n\n" in message)
                ok_("OhNoz" in message)
            else:
                assert False, "Did not raise ThreadException as expected!"


    class watchers:
        # NOTE: it's initially tempting to consider using mocks or stub
        # Responder instances for many of these, but it really doesn't save
        # appreciable runtime or code read/write time.
        # NOTE: these strictly test interactions between
        # StreamWatcher/Responder and their host Runner; Responder-only tests
        # are in tests/watchers.py.

        def nothing_is_written_to_stdin_by_default(self):
            # NOTE: technically if some goofus ran the tests by hand and mashed
            # keys while doing so...this would fail. LOL?
            # NOTE: this test seems not too useful but is a) a sanity test and
            # b) guards against e.g. breaking the autoresponder such that it
            # responds to "" or "\n" or etc.
            klass = self._mock_stdin_writer()
            self._runner(klass=klass).run(_)
            ok_(not klass.write_proc_stdin.called)

        def _expect_response(self, **kwargs):
            """
            Execute a run() w/ ``watchers`` set from ``responses``.

            Any other ``**kwargs`` given are passed direct to ``_runner()``.

            :returns: The mocked ``write_proc_stdin`` method of the runner.
            """
            watchers = [
                Responder(pattern=key, response=value)
                for key, value in iteritems(kwargs.pop('responses'))
            ]
            kwargs['klass'] = klass = self._mock_stdin_writer()
            runner = self._runner(**kwargs)
            runner.run(_, watchers=watchers, hide=True)
            return klass.write_proc_stdin

        def watchers_responses_get_written_to_proc_stdin(self):
            self._expect_response(
                out="the house was empty",
                responses={'empty': 'handed'},
            ).assert_called_once_with("handed")

        def multiple_hits_yields_multiple_responses(self):
            holla = call('how high?')
            self._expect_response(
                out="jump, wait, jump, wait",
                responses={'jump': 'how high?'},
            ).assert_has_calls([holla, holla])

        def chunk_sizes_smaller_than_patterns_still_work_ok(self):
            klass = self._mock_stdin_writer()
            klass.read_chunk_size = 1 # < len('jump')
            responder = Responder('jump', 'how high?')
            runner = self._runner(klass=klass, out="jump, wait, jump, wait")
            runner.run(_, watchers=[responder], hide=True)
            holla = call('how high?')
            # Responses happened, period.
            klass.write_proc_stdin.assert_has_calls([holla, holla])
            # And there weren't duplicates!
            eq_(len(klass.write_proc_stdin.call_args_list), 2)

        def both_out_and_err_are_scanned(self):
            bye = call("goodbye")
            # Would only be one 'bye' if only scanning stdout
            self._expect_response(
                out="hello my name is inigo",
                err="hello how are you",
                responses={"hello": "goodbye"},
            ).assert_has_calls([bye, bye])

        def multiple_patterns_works_as_expected(self):
            calls = [call('betty'), call('carnival')]
            # Technically, I'd expect 'betty' to get called before 'carnival',
            # but under Python 3 it's reliably backwards from Python 2.
            # In real world situations where each prompt sits & waits for its
            # response, this probably wouldn't be an issue, so using
            # any_order=True for now. Thanks again Python 3.
            self._expect_response(
                out="beep boop I am a robot",
                responses={'boop': 'betty', 'robot': 'carnival'},
            ).assert_has_calls(calls, any_order=True)

        def multiple_patterns_across_both_streams(self):
            responses = {
                'boop': 'betty',
                'robot': 'carnival',
                'Destroy': 'your ego',
                'humans': 'are awful',
            }
            calls = map(lambda x: call(x), responses.values())
            # CANNOT assume order due to simultaneous streams.
            # If we didn't say any_order=True we could get race condition fails
            self._expect_response(
                out="beep boop, I am a robot",
                err="Destroy all humans!",
                responses=responses,
            ).assert_has_calls(calls, any_order=True)

        def honors_watchers_config_option(self):
            klass = self._mock_stdin_writer()
            responder = Responder("my stdout", "and my axe")
            runner = self._runner(
                out="this is my stdout", # yielded stdout
                klass=klass, # mocked stdin writer
                run={'watchers': [responder]}, # ends up as config override
            )
            runner.run(_, hide=True)
            klass.write_proc_stdin.assert_called_once_with("and my axe")

        def kwarg_overrides_config(self):
            # TODO: how to handle use cases where merging, not overriding, is
            # the expected/unsurprising default? probably another config-only
            # (not kwarg) setting, e.g. run.merge_responses?
            # TODO: now that this stuff is list, not dict, based, it should be
            # easier...BUT how to handle removal of defaults from config? Maybe
            # just document to be careful using the config as it won't _be_
            # overridden? (Users can always explicitly set the config to be
            # empty-list if they want kwargs to be the entire set of
            # watchers...right?)
            klass = self._mock_stdin_writer()
            conf = Responder("my stdout", "and my axe")
            kwarg = Responder("my stdout", "and my body spray")
            runner = self._runner(
                out="this is my stdout", # yielded stdout
                klass=klass, # mocked stdin writer
                run={'watchers': [conf]}, # ends up as config override
            )
            runner.run(_, hide=True, watchers=[kwarg])
            klass.write_proc_stdin.assert_called_once_with("and my body spray")

    class io_sleeping:
        # NOTE: there's an explicit CPU-measuring test in the integration suite
        # which ensures the *point* of the sleeping - avoiding CPU hogging - is
        # actually functioning. These tests below just unit-test the mechanisms
        # around the sleep functionality (ensuring they are visible and can be
        # altered as needed).
        def input_sleep_attribute_defaults_to_hundredth_of_second(self):
            eq_(Runner(Context()).input_sleep, 0.01)

        @mock_subprocess()
        def subclasses_can_override_input_sleep(self):
            class MyRunner(_Dummy):
                input_sleep = 0.007
            with patch('invoke.runners.time') as mock_time:
                MyRunner(Context()).run(
                    _,
                    in_stream=StringIO("foo"),
                    out_stream=StringIO(), # null output to not pollute tests
                )
            eq_(mock_time.sleep.call_args_list, [call(0.007)] * 3)

    class stdin_mirroring:
        def _test_mirroring(
            self,
            expect_mirroring,
            **kwargs
        ):
            # Setup
            fake_in = "I'm typing!"
            output = Mock()
            input_ = StringIO(fake_in)
            input_is_pty = kwargs.pop('in_pty', None)

            class MyRunner(_Dummy):
                def should_echo_stdin(self, input_, output):
                    # Fake result of isatty() test here and only here; if we do
                    # this farther up, it will affect stuff trying to run
                    # termios & such, which is harder to mock successfully.
                    if input_is_pty is not None:
                        input_.isatty = lambda: input_is_pty
                    return super(MyRunner, self).should_echo_stdin(
                        input_, output)

            # Execute basic command with given parameters
            self._run(
                _,
                klass=MyRunner,
                in_stream=input_,
                out_stream=output,
                **kwargs
            )
            # Examine mocked output stream to see if it was mirrored to
            if expect_mirroring:
                eq_(
                    output.write.call_args_list,
                    list(map(lambda x: call(x), fake_in))
                )
                eq_(len(output.flush.call_args_list), len(fake_in))
            # Or not mirrored to
            else:
                eq_(output.write.call_args_list, [])

        def when_pty_is_True_no_mirroring_occurs(self):
            self._test_mirroring(
                pty=True,
                expect_mirroring=False,
            )

        def when_pty_is_False_we_write_in_stream_back_to_out_stream(self):
            self._test_mirroring(
                pty=False,
                in_pty=True,
                expect_mirroring=True,
            )

        def mirroring_is_skipped_when_our_input_is_not_a_tty(self):
            self._test_mirroring(
                in_pty=False,
                expect_mirroring=False,
            )

        def mirroring_can_be_forced_on(self):
            self._test_mirroring(
                # Subprocess pty normally disables echoing
                pty=True,
                # But then we forcibly enable it
                echo_stdin=True,
                # And expect it to happen
                expect_mirroring=True,
            )

        def mirroring_can_be_forced_off(self):
            # Make subprocess pty False, stdin tty True, echo_stdin False,
            # prove no mirroring
            self._test_mirroring(
                # Subprocess lack of pty normally enables echoing
                pty=False,
                # Provided the controlling terminal _is_ a tty
                in_pty=True,
                # But then we forcibly disable it
                echo_stdin=False,
                # And expect it to not happen
                expect_mirroring=False,
            )

        def mirroring_honors_configuration(self):
            self._test_mirroring(
                pty=False,
                in_pty=True,
                settings={'run': {'echo_stdin': False}},
                expect_mirroring=False,
            )

        @trap
        @skip_if_windows
        @patch('invoke.runners.sys.stdin')
        @patch('invoke.platform.fcntl.ioctl')
        @patch('invoke.platform.os')
        @patch('invoke.platform.termios')
        @patch('invoke.platform.tty')
        @patch('invoke.platform.select')
        # NOTE: the no-fileno edition is handled at top of this local test
        # class, in the base case test.
        def reads_FIONREAD_bytes_from_stdin_when_fileno(
            self, select, tty, termios, mock_os, ioctl, stdin
        ):
            # Set stdin up as a file-like buffer which passes has_fileno
            stdin.fileno.return_value = 17 # arbitrary
            stdin_data = list("boo!")
            def fakeread(n):
                # Why is there no slice version of pop()?
                data = stdin_data[:n]
                del stdin_data[:n]
                return ''.join(data)
            stdin.read.side_effect = fakeread
            # Without mocking this, we'll always get errors checking the above
            # bogus fileno()
            mock_os.tcgetpgrp.return_value = None
            # Ensure select() only spits back stdin one time, despite there
            # being multiple bytes to read (this at least partly fakes behavior
            # from issue #58)
            select.select.side_effect = chain(
                [([stdin], [], [])],
                repeat(([], [], [])),
            )
            # Have ioctl yield our multiple number of bytes when called with
            # FIONREAD
            def fake_ioctl(fd, cmd, buf):
                # This works since each mocked attr will still be its own mock
                # object with a distinct 'is' identity.
                if cmd is termios.FIONREAD:
                    return struct.pack('h', len(stdin_data))
            ioctl.side_effect = fake_ioctl
            # Set up our runner as one w/ mocked stdin writing (simplest way to
            # assert how the reads & writes are happening)
            klass = self._mock_stdin_writer()
            self._runner(klass=klass).run(_)
            klass.write_proc_stdin.assert_called_once_with("boo!")

    class character_buffered_stdin:
        @skip_if_windows
        @patch('invoke.platform.tty')
        @patch('invoke.platform.termios') # stub
        def setcbreak_called_on_tty_stdins(self, mock_termios, mock_tty):
            self._run(_)
            mock_tty.setcbreak.assert_called_with(sys.stdin)

        @skip_if_windows
        @patch('invoke.platform.tty')
        def setcbreak_not_called_on_non_tty_stdins(self, mock_tty):
            self._run(_, in_stream=StringIO())
            ok_(not mock_tty.setcbreak.called)

        @skip_if_windows
        @patch('invoke.platform.tty')
        @patch('invoke.platform.os')
        def setcbreak_not_called_if_process_not_foregrounded(
            self, mock_os, mock_tty,
        ):
            # Re issue #439.
            mock_os.getpgrp.return_value = 1337
            mock_os.tcgetpgrp.return_value = 1338
            self._run(_)
            ok_(not mock_tty.setcbreak.called)
            # Sanity
            mock_os.tcgetpgrp.assert_called_once_with(sys.stdin.fileno())

        @skip_if_windows
        @patch('invoke.platform.tty') # stub
        @patch('invoke.platform.termios')
        def tty_stdins_have_settings_restored_by_default(
            self, mock_termios, mock_tty
        ):
            sentinel = [1, 7, 3, 27]
            mock_termios.tcgetattr.return_value = sentinel
            self._run(_)
            mock_termios.tcsetattr.assert_called_once_with(
                sys.stdin, mock_termios.TCSADRAIN, sentinel
            )

        @skip_if_windows
        @patch('invoke.platform.tty') # stub
        @patch('invoke.platform.termios')
        def tty_stdins_have_settings_restored_on_KeyboardInterrupt(
            self, mock_termios, mock_tty
        ):
            # This test is re: GH issue #303
            # tcgetattr returning some arbitrary value
            sentinel = [1, 7, 3, 27]
            mock_termios.tcgetattr.return_value = sentinel
            # Don't actually bubble up the KeyboardInterrupt...
            try:
                self._run(_, klass=_KeyboardInterruptingRunner)
            except KeyboardInterrupt:
                pass
            # Did we restore settings?!
            mock_termios.tcsetattr.assert_called_once_with(
                sys.stdin, mock_termios.TCSADRAIN, sentinel
            )

    class send_interrupt:
        def _run_with_mocked_interrupt(self, klass):
            runner = klass(Context())
            runner.send_interrupt = Mock()
            try:
                runner.run(_)
            except:
                pass
            return runner

        def called_on_KeyboardInterrupt(self):
            runner = self._run_with_mocked_interrupt(
                _KeyboardInterruptingRunner
            )
            assert runner.send_interrupt.called

        def not_called_for_other_exceptions(self):
            class _GenericExceptingRunner(_Dummy):
                def wait(self):
                    raise Exception
            runner = self._run_with_mocked_interrupt(_GenericExceptingRunner)
            assert not runner.send_interrupt.called

        def sends_escape_byte_sequence(self):
            for pty in (True, False):
                runner = _KeyboardInterruptingRunner(Context())
                mock_stdin = Mock()
                runner.write_proc_stdin = mock_stdin
                runner.run(_, pty=pty)
                mock_stdin.assert_called_once_with(u'\x03')

    class stop:
        def always_runs_no_matter_what(self):
            class _ExceptingRunner(_Dummy):
                def wait(self):
                    raise OhNoz()

            runner = _ExceptingRunner(context=Context())
            runner.stop = Mock()
            try:
                runner.run(_)
            except OhNoz:
                runner.stop.assert_called_once_with()
            else:
                assert False, "_ExceptingRunner did not except!"


class _FastLocal(Local):
    # Neuter this for same reason as in _Dummy above
    input_sleep = 0


class Local_(Spec):
    def _run(self, *args, **kwargs):
        return _run(*args, **dict(kwargs, klass=_FastLocal))

    def _runner(self, *args, **kwargs):
        return _runner(*args, **dict(kwargs, klass=_FastLocal))

    class pty:
        @mock_pty()
        def when_pty_True_we_use_pty_fork_and_os_exec(self):
            "when pty=True, we use pty.fork and os.exec*"
            self._run(_, pty=True)
            # @mock_pty's asserts check os/pty calls for us.

        @mock_pty(insert_os=True)
        def _expect_exit_check(self, exited, mock_os):
            if exited:
                expected_check = mock_os.WIFEXITED
                expected_get = mock_os.WEXITSTATUS
                unexpected_check = mock_os.WIFSIGNALED
                unexpected_get = mock_os.WTERMSIG
            else:
                expected_check = mock_os.WIFSIGNALED
                expected_get = mock_os.WTERMSIG
                unexpected_check = mock_os.WIFEXITED
                unexpected_get = mock_os.WEXITSTATUS
            expected_check.return_value = True
            unexpected_check.return_value = False
            self._run(_, pty=True)
            exitstatus = mock_os.waitpid.return_value[1]
            expected_get.assert_called_once_with(exitstatus)
            ok_(not unexpected_get.called)

        def pty_uses_WEXITSTATUS_if_WIFEXITED(self):
            self._expect_exit_check(True)

        def pty_uses_WTERMSIG_if_WIFSIGNALED(self):
            self._expect_exit_check(False)

        @mock_pty(insert_os=True)
        def WTERMSIG_result_turned_negative_to_match_subprocess(self, mock_os):
            mock_os.WIFEXITED.return_value = False
            mock_os.WIFSIGNALED.return_value = True
            mock_os.WTERMSIG.return_value = 2
            eq_(self._run(_, pty=True, warn=True).exited, -2)

        @mock_pty()
        def pty_is_set_to_controlling_terminal_size(self):
            self._run(_, pty=True)
            # @mock_pty's asserts check the TIOC[GS]WINSZ calls for us

        def warning_only_fires_once(self):
            # I.e. if implementation checks pty-ness >1 time, only one warning
            # is emitted. This is kinda implementation-specific, but...
            skip()

        @patch('invoke.runners.sys')
        def replaced_stdin_objects_dont_explode(self, mock_sys):
            # Replace sys.stdin with an object lacking .isatty(), which
            # normally causes an AttributeError unless we are being careful.
            mock_sys.stdin = object()
            # Test. If bug is present, this will error.
            runner = Local(Context())
            eq_(runner.should_use_pty(pty=True, fallback=True), False)

        @mock_pty(trailing_error=OSError("Input/output error"))
        def spurious_OSErrors_handled_gracefully(self):
            # Doesn't-blow-up test.
            self._run(_, pty=True)

        @mock_pty(trailing_error=OSError("wat"))
        def non_spurious_OSErrors_bubble_up(self):
            try:
                self._run(_, pty=True)
            except ThreadException as e:
                e = e.exceptions[0]
                eq_(e.type, OSError)
                eq_(str(e.value), "wat")

        class fallback:
            @mock_pty(isatty=False)
            def can_be_overridden_by_kwarg(self):
                self._run(_, pty=True, fallback=False)
                # @mock_pty's asserts will be mad if pty-related os/pty calls
                # didn't fire, so we're done.

            @mock_pty(isatty=False)
            def can_be_overridden_by_config(self):
                self._runner(run={'fallback': False}).run(_, pty=True)
                # @mock_pty's asserts will be mad if pty-related os/pty calls
                # didn't fire, so we're done.

            @trap
            @mock_subprocess(isatty=False)
            def affects_result_pty_value(self, *mocks):
                eq_(self._run(_, pty=True).pty, False)

            @mock_pty(isatty=False)
            def overridden_fallback_affects_result_pty_value(self):
                eq_(self._run(_, pty=True, fallback=False).pty, True)

    class shell:
        @mock_pty(insert_os=True)
        def defaults_to_bash_when_pty_True(self, mock_os):
            self._run(_, pty=True)
            eq_(mock_os.execve.call_args_list[0][0][0], '/bin/bash')

        @mock_subprocess(insert_Popen=True)
        def defaults_to_bash_when_pty_False(self, mock_Popen):
            self._run(_, pty=False)
            eq_(mock_Popen.call_args_list[0][1]['executable'], '/bin/bash')

        @mock_pty(insert_os=True)
        def may_be_overridden_when_pty_True(self, mock_os):
            self._run(_, pty=True, shell='/bin/zsh')
            eq_(mock_os.execve.call_args_list[0][0][0], '/bin/zsh')

        @mock_subprocess(insert_Popen=True)
        def may_be_overridden_when_pty_False(self, mock_Popen):
            self._run(_, pty=False, shell='/bin/zsh')
            eq_(mock_Popen.call_args_list[0][1]['executable'], '/bin/zsh')

    class env:
        # NOTE: update-vs-replace semantics are tested 'purely' up above in
        # regular Runner tests.

        @mock_subprocess(insert_Popen=True)
        def uses_Popen_kwarg_for_pty_False(self, mock_Popen):
            self._run(_, pty=False, env={'FOO': 'BAR'})
            expected = dict(os.environ, FOO='BAR')
            eq_(
                mock_Popen.call_args_list[0][1]['env'],
                expected
            )

        @mock_pty(insert_os=True)
        def uses_execve_for_pty_True(self, mock_os):
            type(mock_os).environ = {'OTHERVAR': 'OTHERVAL'}
            self._run(_, pty=True, env={'FOO': 'BAR'})
            expected = {'OTHERVAR': 'OTHERVAL', 'FOO': 'BAR'}
            eq_(
                mock_os.execve.call_args_list[0][0][2],
                expected
            )


class Result_(Spec):
    def nothing_is_required(self):
        Result()

    def first_posarg_is_stdout(self):
        eq_(Result("foo").stdout, "foo")

    def command_defaults_to_empty_string(self):
        eq_(Result().command, "")

    def shell_defaults_to_empty_string(self):
        eq_(Result().shell, "")

    def env_defaults_to_empty_dict(self):
        eq_(Result().env, {})

    def stdout_defaults_to_empty_string(self):
        eq_(Result().stdout, u"")

    def stderr_defaults_to_empty_string(self):
        eq_(Result().stderr, u"")

    def exited_defaults_to_zero(self):
        eq_(Result().exited, 0)

    def pty_defaults_to_False(self):
        eq_(Result().pty, False)

    def repr_contains_useful_info(self):
        eq_(repr(Result(command="foo")), "<Result cmd='foo' exited=0>")
