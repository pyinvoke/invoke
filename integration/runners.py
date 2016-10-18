import os
import platform
import time

from mock import Mock
from spec import Spec, eq_, ok_, skip

from invoke import (
    run, Local, Context, ThreadException, Responder, FailingResponder,
    WatcherError, Failure
)
from invoke.util import ExceptionHandlingThread

from _util import assert_cpu_usage


PYPY = platform.python_implementation() == 'PyPy'

class Runner_(Spec):
    def setup(self):
        os.chdir(os.path.join(os.path.dirname(__file__), '_support'))

    class responding:
        # TODO: update respond_*.py so they timeout instead of hanging forever
        # when not being responded to

        def base_case(self):
            # Basic "doesn't explode" test: respond.py will exit nonzero unless
            # this works, causing a Failure.
            watcher = Responder(r"What's the password\?", "Rosebud\n")
            # Gotta give -u or Python will line-buffer its stdout, so we'll
            # never actually see the prompt.
            run("python -u respond_base.py", watchers=[watcher], hide=True)

        def both_streams(self):
            watchers = [
                Responder("standard out", "with it\n"),
                Responder("standard error", "between chair and keyboard\n"),
            ]
            run("python -u respond_both.py", watchers=watchers, hide=True)

        def watcher_errors_become_Failures(self):
            watcher = FailingResponder(
                pattern=r"What's the password\?",
                response="Rosebud\n",
                sentinel="You're not Citizen Kane!",
            )
            try:
                run("python -u respond_fail.py", watchers=[watcher], hide=True)
            except Failure as e:
                ok_(isinstance(e.reason, WatcherError))
                eq_(e.result.exited, None)
            else:
                assert False, "Did not raise Failure!"

    class stdin_mirroring:
        def piped_stdin_is_not_conflated_with_mocked_stdin(self):
            # Re: GH issue #308
            # Will die on broken-pipe OSError if bug is present.
            run("echo 'lollerskates' | inv -c nested_or_piped foo", hide=True)

        def nested_invoke_sessions_not_conflated_with_mocked_stdin(self):
            # Also re: GH issue #308. This one will just hang forever. Woo!
            run("inv -c nested_or_piped calls_foo", hide=True)

        def isnt_cpu_heavy(self):
            "stdin mirroring isn't CPU-heavy"
            # CPU measurement under PyPy is...rather different. NBD.
            if PYPY:
                skip()
            with assert_cpu_usage(lt=5.0):
                run("python -u busywork.py 10", pty=True, hide=True)

    class interrupts:
        def _run_and_kill(self, pty):
            def bg_body():
                # No reliable way to detect "an exception happened in the inner
                # child that wasn't KeyboardInterrupt", so best we can do is:
                # * Ensure exited 130
                # * Get mad if any output is seen that doesn't look like
                # KeyboardInterrupt stacktrace (because it's probably some
                # OTHER stacktrace).
                pty_flag = "--pty" if pty else "--no-pty"
                result = run(
                    "inv -c signal_tasks expect SIGINT {0}".format(pty_flag),
                    hide=True,
                    warn=True,
                )
                bad_signal = result.exited != 130
                output = result.stdout + result.stderr
                had_keyboardint = 'KeyboardInterrupt' in output
                if bad_signal or (output and not had_keyboardint):
                    err = "Subprocess had output and/or bad exit:"
                    raise Exception("{0}\n\n{1}".format(err, result))

            # Execute sub-invoke in a thread so we can talk to its subprocess
            # while it's running.
            # TODO: useful async API for run() which at least wraps threads for
            # you, and exposes the inner PID
            bg = ExceptionHandlingThread(target=bg_body)
            bg.start()
            # Wait a bit to ensure subprocess is in the right state & not still
            # starting up (lolpython?). NOTE: if you bump this you must also
            # bump the `signal.alarm` call within _support/signaling.py!
            # Otherwise both tests will always fail as the ALARM fires
            # (resulting in "Never got any signals!" in debug log) before this
            # here sleep finishes.
            time.sleep(2 if PYPY else 1)
            # Send expected signal (use pty to ensure no intermediate 'sh'
            # processes on Linux; is of no consequence on Darwin.)
            interpreter = 'pypy' if PYPY else 'python'
            cmd = "pkill -INT -f \"{0}.*inv -c signal_tasks\""
            run(cmd.format(interpreter), pty=True)
            # Rejoin subprocess thread & check for exceptions
            bg.join()
            wrapper = bg.exception()
            if wrapper:
                # This is an ExceptionWrapper, not an actual exception, since
                # most places using ExceptionHandlingThread need access to the
                # thread's arguments & such. We just want the exception here.
                raise wrapper.value

        def pty_True(self):
            self._run_and_kill(pty=True)

        def pty_False(self):
            self._run_and_kill(pty=False)

    class IO_hangs:
        "IO hangs"
        def _hang_on_full_pipe(self, pty):
            class Whoops(Exception):
                pass
            runner = Local(Context())
            # Force runner IO thread-body method to raise an exception to mimic
            # real world encoding explosions/etc. When bug is present, this
            # will make the test hang until forcibly terminated.
            runner.handle_stdout = Mock(side_effect=Whoops, __name__='sigh')
            # NOTE: both Darwin (10.10) and Linux (Travis' docker image) have
            # this file. It's plenty large enough to fill most pipe buffers,
            # which is the triggering behavior.
            try:
                runner.run("cat /usr/share/dict/words", pty=pty)
            except ThreadException as e:
                eq_(len(e.exceptions), 1)
                ok_(e.exceptions[0].type is Whoops)
            else:
                assert False, "Did not receive expected ThreadException!"

        def pty_subproc_should_not_hang_if_IO_thread_has_an_exception(self):
            self._hang_on_full_pipe(pty=True)

        def nonpty_subproc_should_not_hang_if_IO_thread_has_an_exception(self):
            self._hang_on_full_pipe(pty=False)
