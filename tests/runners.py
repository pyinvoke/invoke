import locale
import sys
import types
from invoke.vendor.six import StringIO, b
from signal import SIGINT, SIGTERM

from spec import (
    Spec, trap, eq_, skip, ok_, raises, assert_contains, assert_not_contains
)
from mock import patch, Mock, call

from invoke import Runner, Local, Context, Config, Failure, ThreadException
from invoke.platform import WINDOWS

from _util import mock_subprocess, mock_pty, skip_if_windows


# Dummy command that will blow up if it ever truly hits a real shell.
_ = "nope"

class _Dummy(Runner):
    """
    Dummy runner subclass that does minimum work required to execute run().
    """
    # Neuter the input loop sleep, so tests aren't slow (at the expense of CPU,
    # which isn't a problem for testing).
    input_sleep = 0

    def start(self, command):
        pass

    def read_stdout(self, num_bytes):
        return ""

    def read_stderr(self, num_bytes):
        return ""

    def write_stdin(self, data):
        pass

    def default_encoding(self):
        return "US-ASCII"

    def wait(self):
        pass

    def returncode(self):
        return 0

    def send_interrupt(self):
        pass


# Runner that fakes ^C during subprocess exec
class _KeyboardInterruptingRunner(_Dummy):
    def wait(self):
        raise KeyboardInterrupt


class OhNoz(Exception):
    pass


def _expect_encoding(codecs, encoding):
    assert codecs.iterdecode.called
    for c in codecs.iterdecode.call_args_list:
        eq_(c[0][1], encoding)

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
    out_file = StringIO(out)
    err_file = StringIO(err)
    runner.read_stdout = out_file.read
    runner.read_stderr = err_file.read
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
        Return new _Dummy-based class whose write_stdin() method is a mock.
        """
        class MockedStdin(_Dummy):
            pass
        MockedStdin.write_stdin = Mock()
        return MockedStdin


    class init:
        "__init__"
        def takes_a_context_instance(self):
            c = Context()
            eq_(Runner(c).context, c)

        @raises(TypeError)
        def context_instance_is_required(self):
            Runner()

    class warn:
        def honors_config(self):
            runner = self._runner(run={'warn': True}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run(_)

        def kwarg_beats_config(self):
            runner = self._runner(run={'warn': False}, exits=1)
            # Doesn't raise Failure -> all good
            runner.run(_, warn=True)

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

    class return_value:
        def return_code_in_result(self):
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
        # Use UTF-7 as a valid encoding unlikely to be a real default
        def defaults_to_encoding_method_result(self):
            runner = self._runner()
            encoding = 'UTF-7'
            runner.default_encoding = Mock(return_value=encoding)
            with patch('invoke.runners.codecs') as codecs:
                runner.run(_)
                runner.default_encoding.assert_called_with()
                _expect_encoding(codecs, encoding)

        def honors_config(self):
            with patch('invoke.runners.codecs') as codecs:
                c = Context(Config(overrides={'run': {'encoding': 'UTF-7'}}))
                _Dummy(c).run(_)
                _expect_encoding(codecs, 'UTF-7')

        def honors_kwarg(self):
            skip()

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
            # Check that mocked writer was called w/ expected data
            # stdin mirroring occurs byte-by-byte
            calls = list(map(lambda x: call(b(x)), "Text!"))
            klass.write_stdin.assert_has_calls(calls, any_order=False)

        def can_be_overridden(self):
            klass = self._mock_stdin_writer()
            in_stream = StringIO("Hey, listen!")
            self._runner(klass=klass).run(
                _,
                in_stream=in_stream,
                out_stream=StringIO(),
            )
            # stdin mirroring occurs byte-by-byte
            calls = list(map(lambda x: call(b(x)), "Hey, listen!"))
            klass.write_stdin.assert_has_calls(calls, any_order=False)

        @patch('invoke.runners.debug')
        def exceptions_get_logged(self, mock_debug):
            # Make write_stdin asplode
            klass = self._mock_stdin_writer()
            klass.write_stdin.side_effect = OhNoz("oh god why")
            # Execute with some stdin to trigger that asplode (but skip the
            # actual bubbled-up raising of it so we can check things out)
            try:
                stdin = StringIO("non-empty")
                self._runner(klass=klass).run(_, in_stream=stdin)
            except ThreadException:
                pass
            # Assert debug() was called w/ expected format
            # TODO: make the debug call a method on IOThread, then make thread
            # class configurable somewhere in Runner, and pass in a customized
            # IOThread that has a Mock for that method?
            mock_debug.assert_called_with("Encountered exception OhNoz('oh god why',) in IO thread for 'handle_stdin'") # noqa

    class failure_handling:
        @raises(Failure)
        def fast_failures(self):
            self._runner(exits=1).run(_)

        def non_one_return_codes_still_act_as_failure(self):
            r = self._runner(exits=17).run(_, warn=True)
            eq_(r.failed, True)

        def Failure_repr_includes_stderr(self):
            try:
                self._runner(exits=1, err="ohnoz").run(_, hide=True)
                assert false # noqa. Ensure failure to Failure fails
            except Failure as f:
                r = repr(f)
                err = "Sentinel 'ohnoz' not found in {0!r}".format(r)
                assert 'ohnoz' in r, err

        def Failure_repr_should_present_stdout_when_pty_was_used(self):
            try:
                # NOTE: using mocked stdout because that's what ptys do as
                # well. when pty=True, nothing's even trying to read stderr.
                self._runner(exits=1, out="ohnoz").run(_, hide=True, pty=True)
                assert false # noqa. Ensure failure to Failure fails
            except Failure as f:
                r = repr(f)
                err = "Sentinel 'ohnoz' not found in {0!r}".format(r)
                assert 'ohnoz' in r, err

    class threading:
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

    class responding:
        def nothing_is_written_to_stdin_by_default(self):
            # NOTE: technically if some goofus ran the tests by hand and mashed
            # keys while doing so...this would fail. LOL?
            # NOTE: this test seems not too useful but is a) a sanity test and
            # b) guards against e.g. breaking the autoresponder such that it
            # responds to "" or "\n" or etc.
            klass = self._mock_stdin_writer()
            self._runner(klass=klass).run(_)
            ok_(not klass.write_stdin.called)

        def _expect_response(self, **kwargs):
            """
            Execute a run() w/ ``responses`` set & _runner() ``kwargs`` given.

            :returns: The mocked ``write_stdin`` method of the runner.
            """
            klass = self._mock_stdin_writer()
            kwargs['klass'] = klass
            runner = self._runner(**kwargs)
            runner.run(_, responses=kwargs['responses'], hide=True)
            return klass.write_stdin

        def string_keys_in_responses_kwarg_yield_values_as_stdin_writes(self):
            self._expect_response(
                out="the house was empty",
                responses={'empty': 'handed'},
            ).assert_called_once_with(b("handed"))

        def regex_keys_also_work(self):
            self._expect_response(
                out="technically, it's still debt",
                responses={r'tech.*debt': 'pay it down'},
            ).assert_called_once_with(b('pay it down'))

        def multiple_hits_yields_multiple_responses(self):
            holla = call(b('how high?'))
            self._expect_response(
                out="jump, wait, jump, wait",
                responses={'jump': 'how high?'},
            ).assert_has_calls([holla, holla])

        def chunk_sizes_smaller_than_patterns_still_work_ok(self):
            klass = self._mock_stdin_writer()
            klass.read_chunk_size = 1 # < len('jump')
            responses = {'jump': 'how high?'}
            runner = self._runner(klass=klass, out="jump, wait, jump, wait")
            runner.run(_, responses=responses, hide=True)
            holla = call(b('how high?'))
            # Responses happened, period.
            klass.write_stdin.assert_has_calls([holla, holla])
            # And there weren't duplicates!
            eq_(len(klass.write_stdin.call_args_list), 2)

        def patterns_span_multiple_lines(self):
            output = """
You only call me
when you have a problem
You never call me
Just to say hi
"""
            self._expect_response(
                out=output,
                responses={r'call.*problem': 'So sorry'},
            ).assert_called_once_with(b('So sorry'))

        def both_out_and_err_are_scanned(self):
            bye = call(b("goodbye"))
            # Would only be one 'bye' if only scanning stdout
            self._expect_response(
                out="hello my name is inigo",
                err="hello how are you",
                responses={"hello": "goodbye"},
            ).assert_has_calls([bye, bye])

        def multiple_patterns_works_as_expected(self):
            calls = [call(b('betty')), call(b('carnival'))]
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
            calls = map(lambda x: call(b(x)), responses.values())
            # CANNOT assume order due to simultaneous streams.
            # If we didn't say any_order=True we could get race condition fails
            self._expect_response(
                out="beep boop, I am a robot",
                err="Destroy all humans!",
                responses=responses,
            ).assert_has_calls(calls, any_order=True)

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
                def echo_stdin(self, input_, output):
                    # Fake result of isatty() test here and only here; if we do
                    # this farther up, it will affect stuff trying to run
                    # termios & such, which is harder to mock successfully.
                    if input_is_pty is not None:
                        input_.isatty = lambda: input_is_pty
                    return super(MyRunner, self).echo_stdin(input_, output)

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
                eq_(output.write.call_args_list, list(map(call, fake_in)))
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
            eq_(mock_tty.setcbreak.call_args_list, [])

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

    class keyboard_interrupts_act_transparently:
        def _run_with_mocked_interrupt(self, klass):
            runner = klass(Context(config=Config()))
            runner.send_interrupt = Mock()
            try:
                runner.run(_)
            except:
                pass
            return runner

        def send_interrupt_called_on_KeyboardInterrupt(self):
            runner = self._run_with_mocked_interrupt(
                _KeyboardInterruptingRunner
            )
            assert runner.send_interrupt.called

        def send_interrupt_not_called_for_other_exceptions(self):
            class _GenericExceptingRunner(_Dummy):
                def wait(self):
                    raise Exception
            runner = self._run_with_mocked_interrupt(_GenericExceptingRunner)
            assert not runner.send_interrupt.called

        def KeyboardInterrupt_is_still_raised(self):
            raised = None
            try:
                self._run(_, klass=_KeyboardInterruptingRunner)
            except KeyboardInterrupt as e:
                raised = e
            assert raised is not None


class _FastLocal(Local):
    # Neuter this for same reason as in _Dummy above
    input_sleep = 0

class _KeyboardInterruptingFastLocal(_FastLocal):
    def wait(self):
        raise KeyboardInterrupt


class Local_(Spec):
    def _run(self, *args, **kwargs):
        return _run(*args, **dict(kwargs, klass=_FastLocal))

    def _runner(self, *args, **kwargs):
        return _runner(*args, **dict(kwargs, klass=_FastLocal))

    class pty_and_pty_fallback:
        @mock_pty()
        def when_pty_True_we_use_pty_fork_and_os_exec(self):
            "when pty=True, we use pty.fork and os.exec*"
            self._run(_, pty=True)
            # @mock_pty's asserts check os/pty calls for us.

        @mock_pty()
        def pty_is_set_to_controlling_terminal_size(self):
            self._run(_, pty=True)
            # @mock_pty's asserts check fcntl calls for us

        def warning_only_fires_once(self):
            # I.e. if implementation checks pty-ness >1 time, only one warning
            # is emitted. This is kinda implementation-specific, but...
            skip()

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
        def fallback_affects_result_pty_value(self, *mocks):
            eq_(self._run(_, pty=True).pty, False)

        @mock_pty(isatty=False)
        def overridden_fallback_affects_result_pty_value(self):
            eq_(self._run(_, pty=True, fallback=False).pty, True)

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

    class encoding:
        @mock_subprocess()
        def uses_locale_module_for_desired_encoding(self):
            with patch('invoke.runners.codecs') as codecs:
                self._run(_)
                local_encoding = locale.getpreferredencoding(False)
                _expect_encoding(codecs, local_encoding)

    class send_interrupt:
        def  _run(self, pty):
            runner = _KeyboardInterruptingFastLocal(Context(config=Config()))
            try:
                runner.run(_, pty=pty)
            except KeyboardInterrupt:
                pass
            return runner

        @mock_pty(skip_asserts=True)
        def uses_os_kill_when_pty_True(self):
            with patch('invoke.runners.os.kill') as kill:
                runner = self._run(pty=True)
                kill.assert_called_once_with(runner.pid, SIGINT)

        @mock_subprocess()
        def uses_subprocess_send_signal_when_pty_False(self):
            runner = self._run(pty=False)
            # Don't see a great way to test this w/o replicating the logic.
            expected = SIGTERM if WINDOWS else SIGINT
            runner.process.send_signal.assert_called_once_with(expected)
