import sys
import os

from spec import eq_, skip, Spec, raises, ok_, trap

from invoke.runner import Runner, run
from invoke.exceptions import Failure

from _utils import support


def _run(returns=None, **kwargs):
    """
    Create a Runner w/ retval reflecting ``returns`` & call ``run(**kwargs)``.
    """
    # Set up return value tuple for Runner.run
    returns = returns or {}
    returns.setdefault('exited', 0)
    value = map(
        lambda x: returns.get(x, None),
        ('stdout', 'stderr', 'exited', 'exception'),
    )
    class MockRunner(Runner):
        def run(self, command, warn, hide):
            return value
    # Ensure top level run() uses that runner, provide dummy command.
    kwargs['runner'] = MockRunner
    return run("whatever", **kwargs)


class Run(Spec):
    "run()"

    def setup(self):
        os.chdir(support)
        self.both = "echo foo && ./err bar"
        self.out = "echo foo"
        self.err = "./err bar"
        self.sub = "inv -c pty_output hide_%s"

    class return_value:
        def return_code_in_result(self):
            """
            Result has .return_code (and .exited) containing exit code int
            """
            r = run(self.out, hide='both')
            eq_(r.return_code, 0)
            eq_(r.exited, 0)

        def nonzero_return_code_for_failures(self):
            result = run("false", warn=True)
            eq_(result.exited, 1)
            result = run("goobypls", warn=True, hide='both')
            eq_(result.exited, 127)

        def stdout_attribute_contains_stdout(self):
            eq_(run(self.out, hide='both').stdout, 'foo\n')

        def stderr_attribute_contains_stderr(self):
            eq_(run(self.err, hide='both').stderr, 'bar\n')

        def ok_attr_indicates_success(self):
            eq_(_run().ok, True)
            eq_(_run(returns={'exited': 1}, warn=True).ok, False)

        def failed_attr_indicates_failure(self):
            eq_(_run().failed, False)
            eq_(_run(returns={'exited': 1}, warn=True).failed, True)

        def has_exception_attr(self):
            eq_(_run().exception, None)


    class failure_handling:
        @raises(Failure)
        def fast_failures(self):
            run("false")

        def run_acts_as_success_boolean(self):
            ok_(not run("false", warn=True))
            ok_(run("true"))

        def non_one_return_codes_still_act_as_False(self):
            ok_(not run("goobypls", warn=True, hide='both'))

        def warn_kwarg_allows_continuing_past_failures(self):
            eq_(run("false", warn=True).exited, 1)

        def Failure_repr_includes_stderr(self):
            try:
                run("./err ohnoz && exit 1", hide='both')
                assert false # Ensure failure to Failure fails
            except Failure as f:
                r = repr(f)
                assert 'ohnoz' in r, "Sentinel 'ohnoz' not found in %r" % r

    class output_controls:
        @trap
        def _hide_both(self, val):
            run(self.both, hide=val)
            eq_(sys.stdall.getvalue(), "")

        def hide_both_hides_everything(self):
            self._hide_both('both')

        def hide_True_hides_everything(self):
            self._hide_both(True)

        @trap
        def hide_out_only_hides_stdout(self):
            run(self.both, hide='out')
            eq_(sys.stdout.getvalue().strip(), "")
            eq_(sys.stderr.getvalue().strip(), "bar")

        @trap
        def hide_err_only_hides_stderr(self):
            run(self.both, hide='err')
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "")

        @trap
        def hide_accepts_stderr_alias_for_err(self):
            run(self.both, hide='stderr')
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "")

        @trap
        def hide_accepts_stdout_alias_for_out(self):
            run(self.both, hide='stdout')
            eq_(sys.stdout.getvalue().strip(), "")
            eq_(sys.stderr.getvalue().strip(), "bar")

        def hide_both_hides_both_under_pty(self):
            r = run(self.sub % 'both', hide='both')
            eq_(r.stdout, "")
            eq_(r.stderr, "")

        def hide_out_hides_both_under_pty(self):
            r = run(self.sub % 'out', hide='both')
            eq_(r.stdout, "")
            eq_(r.stderr, "")

        def hide_err_has_no_effect_under_pty(self):
            r = run(self.sub % 'err', hide='both')
            eq_(r.stdout, "foo\r\nbar\r\n")
            eq_(r.stderr, "")

        @trap
        def _no_hiding(self, val):
            r = run(self.both, hide=val)
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "bar")

        def hide_None_hides_nothing(self):
            self._no_hiding(None)

        def hide_False_hides_nothing(self):
            self._no_hiding(False)

        @raises(ValueError)
        def hide_unknown_vals_raises_ValueError(self):
            run("command", hide="what")

        def hide_unknown_vals_mention_value_given_in_error(self):
            value = "penguinmints"
            try:
                run("command", hide=value)
            except ValueError as e:
                msg = "Error from run(hide=xxx) did not tell user what the bad value was!"
                msg += "\nException msg: %s" % e
                ok_(value in str(e), msg)
            else:
                assert False, "run() did not raise ValueError for bad hide= value"

        def hide_does_not_affect_capturing(self):
            eq_(run(self.out, hide='both').stdout, 'foo\n')

    class pseudo_terminals:
        def return_value_indicates_whether_pty_was_used(self):
            eq_(run("true").pty, False)
            eq_(run("true", pty=True).pty, True)

        def pty_defaults_to_off(self):
            eq_(run("true").pty, False)

    class command_echo:
        @trap
        def does_not_echo_commands_run_by_default(self):
            run("echo hi")
            eq_(sys.stdout.getvalue().strip(), "hi")

        @trap
        def when_echo_True_commands_echoed_in_bold(self):
            run("echo hi", echo=True)
            expected = "\033[1;37mecho hi\033[0m\nhi"
            eq_(sys.stdout.getvalue().strip(), expected)

        @trap
        def when_echo_True_and_nocolor_True_commands_not_in_bold(self):
            run("echo hi", echo=True, nocolor=True)
            expected = "echo hi\nhi"
            eq_(sys.stdout.getvalue().strip(), expected)

    #
    # Random edge/corner case junk
    #

    def non_stupid_OSErrors_get_captured(self):
        # Somehow trigger an OSError saying "Input/output error" within
        # pexpect.spawn().interact() & assert it is in result.exception
        skip()

    def KeyboardInterrupt_on_stdin_doesnt_flake(self):
        # E.g. inv test => Ctrl-C halfway => shouldn't get buffer API errors
        skip()

    class funky_characters_in_stdout:
        def basic_nonstandard_characters(self):
            # Crummy "doesn't explode with decode errors" test
            run("cat tree.out", hide='both')

        def nonprinting_bytes(self):
            # Seriously non-printing characters (i.e. non UTF8) also don't asplode
            # load('funky').derp()
            run("echo '\xff'", hide='both')

        def nonprinting_bytes_pty(self):
            # PTY use adds another utf-8 decode spot which can also fail.
            run("echo '\xff'", pty=True, hide='both')


class Local_(Spec):
    def setup(self):
        os.chdir(support)
        self.both = "echo foo && ./err bar"

    def stdout_contains_both_streams_under_pty(self):
        r = run(self.both, hide='both', pty=True)
        eq_(r.stdout, 'foo\r\nbar\r\n')

    def stderr_is_empty_under_pty(self):
        r = run(self.both, hide='both', pty=True)
        eq_(r.stderr, '')
