import os
import sys
import types
from io import BytesIO
from signal import SIGINT, SIGTERM

from invoke.vendor.six import StringIO, b, PY2, iteritems

from spec import (
    Spec, trap, eq_, skip, ok_, raises, assert_contains, assert_not_contains
)
from mock import patch, Mock, call

from invoke import (
    Runner, Local, Context, Config, Failure, ThreadException, Responder,
    WatcherError, UnexpectedExit, StreamWatcher
)
from invoke.platform import WINDOWS

from _util import (
    mock_subprocess, mock_pty, skip_if_windows, Dummy,
    _KeyboardInterruptingRunner, OhNoz, _,
)


def _run(*args, **kwargs):
    klass = kwargs.pop('klass', Dummy)
    settings = kwargs.pop('settings', {})
    context = Context(config=Config(overrides=settings))
    return klass(context).run(*args, **kwargs)

def _runner(out='', err='', **kwargs):
    klass = kwargs.pop('klass', Dummy)
    runner = klass(Context(config=Config(overrides=kwargs)))
    if 'exits' in kwargs:
        runner.returncode = Mock(return_value=kwargs.pop('exits'))
    out_file = BytesIO(b(out))
    err_file = BytesIO(b(err))
    runner.read_proc_stdout = out_file.read
    runner.read_proc_stderr = err_file.read
    return runner


class _FastLocal(Local):
    # Neuter this for same reason as in Dummy above
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

        @patch('invoke.runners.local.sys')
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

    class send_interrupt:
        def _run(self, pty):
            runner = _KeyboardInterruptingFastLocal(Context(config=Config()))
            try:
                runner.run(_, pty=pty)
            except KeyboardInterrupt:
                pass
            return runner

        @mock_pty(skip_asserts=True)
        def uses_os_kill_when_pty_True(self):
            with patch('invoke.runners.local.os.kill') as kill:
                runner = self._run(pty=True)
                kill.assert_called_once_with(runner.pid, SIGINT)

        @mock_subprocess()
        def uses_subprocess_send_signal_when_pty_False(self):
            runner = self._run(pty=False)
            # Don't see a great way to test this w/o replicating the logic.
            expected = SIGTERM if WINDOWS else SIGINT
            runner.process.send_signal.assert_called_once_with(expected)

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
            print(mock_os)
            type(mock_os).environ = {'OTHERVAR': 'OTHERVAL'}
            self._run(_, pty=True, env={'FOO': 'BAR'})
            expected = {'OTHERVAR': 'OTHERVAL', 'FOO': 'BAR'}
            eq_(
                mock_os.execve.call_args_list[0][0][2],
                expected
            )
