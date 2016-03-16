import os

from spec import Spec

from invoke import run

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

    def KeyboardInterrupt_triggers_SIGINT(self):
        # TODO:
        # - my run() of invoke needs to submit the kill signal to the
        # sub-invoke - so we either need an async API now (hrrgh) or I need to
        # just use shelly bits in the top level invocation, e.g. & + kill %1
        # type stuff (needs to work on bash obvs)
        # - then the inner invoke should get KeyboardInterrupt, respond
        # accordingly, and the sub-subprocess of signals.py should receive
        # SIGINT and assert True
        #   - I guess this means it needs a timeout so if the signal does NOT
        #   appear, it doesn't just sleep forever
        #   - check to see if I have prior art for that heh...
        # TODO: figure out whether KeyboardInterrupt is truly always launched
        # when Python receives a SIGINT. May need to just switch everything to
        # signal handling if not (which is probably cleaner regardless).
        # NOTE: we may need to sleep between launch & signal-send, because
        # if we're too fast on the signal, it may get sent before the innermost
        # Python process is actually fully set up w/ its signal handlers...
        run("inv -c signal_tasks expect SIGINT")
