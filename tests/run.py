import sys

from spec import eq_, skip, Spec, raises, ok_, trap

from invoke.run import run
from invoke.exceptions import Failure


class Run(Spec):
    """run()"""
    def return_code_in_result(self):
        r = run("echo 'foo'", hide=True)
        eq_(r.stdout, "foo\n")
        eq_(r.return_code, 0)
        eq_(r.exited, 0)

    def nonzero_return_code_for_failures(self):
        result = run("false", warn=True)
        eq_(result.exited, 1)
        result = run("goobypls", warn=True, hide=True)
        eq_(result.exited, 127)

    @raises(Failure)
    def fast_failures(self):
        run("false")

    def run_acts_as_success_boolean(self):
        ok_(not run("false", warn=True))
        ok_(run("true"))

    def non_one_return_codes_still_act_as_False(self):
        ok_(not run("goobypls", warn=True, hide=True))

    def warn_kwarg_allows_continuing_past_failures(self):
        eq_(run("false", warn=True).exited, 1)

    @trap
    def hide_kwarg_allows_hiding_output(self):
        run("echo 'foo'", hide=True)
        eq_(sys.stdall.getvalue(), "")
