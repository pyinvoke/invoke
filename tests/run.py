import sys

from spec import eq_, skip, Spec, raises, ok_, trap

from invoke.run import run
from invoke.exceptions import Failure


class Run(Spec):
    "run()"
    def return_code_in_result(self):
        r = run("echo 'foo'", hide='both')
        eq_(r.stdout, "foo\n")
        eq_(r.return_code, 0)
        eq_(r.exited, 0)

    def nonzero_return_code_for_failures(self):
        result = run("false", warn=True)
        eq_(result.exited, 1)
        result = run("goobypls", warn=True, hide='both')
        eq_(result.exited, 127)

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

    @trap
    def hide_kwarg_allows_hiding_output(self):
        run("echo 'foo'", hide='both')
        eq_(sys.stdall.getvalue(), "")

    @trap
    def hide_out_only_hides_stdout(self):
        run("echo 'foo' && echo 'bar' 1>&2", hide='out')
        eq_(sys.stdout.getvalue().strip(), "")
        eq_(sys.stderr.getvalue().strip(), "bar")

    @trap
    def hide_err_only_hides_stderr(self):
        run("echo 'foo' && echo 'bar' 1>&2", hide='err')
        eq_(sys.stdout.getvalue().strip(), "foo")
        eq_(sys.stderr.getvalue().strip(), "")

    @trap
    def hide_None_hides_nothing(self):
        run("echo 'foo' && echo 'bar' 1>&2", hide=None)
        eq_(sys.stdout.getvalue().strip(), "foo")
        eq_(sys.stderr.getvalue().strip(), "bar")

    @raises(ValueError)
    def hide_unknown_vals_raises_ValueError(self):
        run("command", hide="what")
