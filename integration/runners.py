import os
import platform
import time

from mock import Mock
from pytest import skip, raises

from invoke import (
    run,
    Local,
    Context,
    ThreadException,
    Responder,
    FailingResponder,
    WatcherError,
    Failure,
    CommandTimedOut,
)

from _util import assert_cpu_usage


PYPY = platform.python_implementation() == "PyPy"


class Runner_:
    def setup(self):
        os.chdir(os.path.join(os.path.dirname(__file__), "_support"))

    class responding:
        def base_case(self):
            # Basic "doesn't explode" test: respond.py will exit nonzero unless
            # this works, causing a Failure.
            watcher = Responder(r"What's the password\?", "Rosebud\n")
            # Gotta give -u or Python will line-buffer its stdout, so we'll
            # never actually see the prompt.
            run(
                "python -u respond_base.py",
                watchers=[watcher],
                hide=True,
                timeout=5,
            )

        def both_streams(self):
            watchers = [
                Responder("standard out", "with it\n"),
                Responder("standard error", "between chair and keyboard\n"),
            ]
            run(
                "python -u respond_both.py",
                watchers=watchers,
                hide=True,
                timeout=5,
            )

        def watcher_errors_become_Failures(self):
            watcher = FailingResponder(
                pattern=r"What's the password\?",
                response="Rosebud\n",
                sentinel="You're not Citizen Kane!",
            )
            try:
                run(
                    "python -u respond_fail.py",
                    watchers=[watcher],
                    hide=True,
                    timeout=5,
                )
            except Failure as e:
                assert isinstance(e.reason, WatcherError)
                assert e.result.exited is None
            else:
                assert False, "Did not raise Failure!"

    class stdin_mirroring:
        def piped_stdin_is_not_conflated_with_mocked_stdin(self):
            # Re: GH issue #308
            # Will die on broken-pipe OSError if bug is present.
            run("echo 'lollerskates' | inv -c nested_or_piped foo", hide=True)

        def nested_invoke_sessions_not_conflated_with_mocked_stdin(self):
            # Also re: GH issue #308. This one will just hang forever. Woo!
            run("inv -c nested_or_piped calls-foo", hide=True)

        def isnt_cpu_heavy(self):
            "stdin mirroring isn't CPU-heavy"
            # CPU measurement under PyPy is...rather different. NBD.
            if PYPY:
                skip()
            # Python 3.5 has been seen using up to ~6.0s CPU time under Travis
            with assert_cpu_usage(lt=7.0):
                run("python -u busywork.py 10", pty=True, hide=True)

        def doesnt_break_when_stdin_exists_but_null(self):
            # Re: #425 - IOError occurs when bug present
            run("inv -c nested_or_piped foo < /dev/null", hide=True)

    class IO_hangs:
        "IO hangs"

        def _hang_on_full_pipe(self, pty):
            class Whoops(Exception):
                pass

            runner = Local(Context())
            # Force runner IO thread-body method to raise an exception to mimic
            # real world encoding explosions/etc. When bug is present, this
            # will make the test hang until forcibly terminated.
            runner.handle_stdout = Mock(side_effect=Whoops, __name__="sigh")
            # NOTE: both Darwin (10.10) and Linux (Travis' docker image) have
            # this file. It's plenty large enough to fill most pipe buffers,
            # which is the triggering behavior.
            try:
                runner.run("cat /usr/share/dict/words", pty=pty)
            except ThreadException as e:
                assert len(e.exceptions) == 1
                assert e.exceptions[0].type is Whoops
            else:
                assert False, "Did not receive expected ThreadException!"

        def pty_subproc_should_not_hang_if_IO_thread_has_an_exception(self):
            self._hang_on_full_pipe(pty=True)

        def nonpty_subproc_should_not_hang_if_IO_thread_has_an_exception(self):
            self._hang_on_full_pipe(pty=False)

    class timeouts:
        def does_not_fire_when_command_quick(self):
            assert run("sleep 1", timeout=5)

        def triggers_exception_when_command_slow(self):
            before = time.time()
            with raises(CommandTimedOut) as info:
                run("sleep 5", timeout=0.5)
            after = time.time()
            # Fudge real time check a bit, <=0.5 typically fails due to
            # overhead etc. May need raising further to avoid races? Meh.
            assert (after - before) <= 0.75
            # Sanity checks of the exception obj
            assert info.value.timeout == 0.5
            assert info.value.result.command == "sleep 5"
