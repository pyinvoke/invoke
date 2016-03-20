import os
import time

from spec import Spec, skip

from invoke import run
from invoke.util import ExceptionHandlingThread

from _util import assert_cpu_usage


class Runner_(Spec):
    def setup(self):
        os.chdir(os.path.join(os.path.dirname(__file__), '_support'))

    class responding:
        # TODO: update respond_*.py so they timeout instead of hanging forever
        # when not being responded to

        def base_case(self):
            # Basic "doesn't explode" test: respond.py will exit nonzero unless
            # this works, causing a Failure.
            responses = {r"What's the password\?": "Rosebud\n"}
            # Gotta give -u or Python will line-buffer its stdout, so we'll
            # never actually see the prompt.
            run("python -u respond_base.py", responses=responses, hide=True)

        def both_streams(self):
            responses = {
                "standard out": "with it\n",
                "standard error": "between chair and keyboard\n",
            }
            run("python -u respond_both.py", responses=responses, hide=True)

        def stdin_mirroring_isnt_cpu_heavy(self):
            "stdin mirroring isn't CPU-heavy"
            with assert_cpu_usage(lt=5.0):
                run("python -u busywork.py 10", pty=True, hide=True)

    class stdin_mirroring:
        def piped_stdin_is_not_conflated_with_mocked_stdin(self):
            # Re: GH issue #308
            # Will die on broken-pipe OSError if bug is present.
            run("echo 'lollerskates' | inv -c nested_or_piped foo", hide=True)

        def nested_invoke_sessions_not_conflated_with_mocked_stdin(self):
            # Also re: GH issue #308. This one will just hang forever. Woo!
            run("inv -c nested_or_piped calls_foo", hide=True)


    class interrupts:
        def _run_and_kill(self, pty):
            def bg_body():
                # TODO: use 'expect exit of 130' when that's implemented Hide
                # output by default, then assume an error & display stderr, if
                # there's any stderr. (There's no reliable way to tell the
                # subprocess raised an exception, because we'll be interrupted
                # before completion, and won't have access to its exit code.)
                pty_flag = "--pty" if pty else "--no-pty"
                result = run(
                    "inv -c signal_tasks expect SIGINT {0}".format(pty_flag),
                    hide=True,
                    warn=True,
                )
                if result.exited != 130 or result.stdout or result.stderr:
                    err = "Subprocess had output and/or bad exit:"
                    raise Exception("{0}\n\n{1}".format(err, result))

            # Execute sub-invoke in a thread so we can talk to its subprocess
            # while it's running.
            # TODO: useful async API for run() which at least wraps threads for
            # you, and exposes the inner PID
            bg = ExceptionHandlingThread(target=bg_body)
            bg.start()
            # Wait a bit to ensure subprocess is in the right state & not still
            # starting up (lolpython?)
            time.sleep(1)
            # Send expected signal (use pty to ensure no intermediate 'sh'
            # processes on Linux; is of no consequence on Darwin.)
            run("pkill -INT -f \"python.*inv -c signal_tasks\"", pty=True)
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
            skip()
