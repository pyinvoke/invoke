from spec import eq_, skip, Spec, raises, ok_

from invoke import run
from invoke.exceptions import Failure


class Run(Spec):
    """run()"""
    def return_code_in_result(self):
        r = run("echo 'foo'")
        eq_(r.stdout, "foo\n")
        eq_(r.return_code, 0)
        eq_(r.exited, 0)

    def nonzero_return_code_for_failures(self):
        result = run("false", warn=True)
        eq_(result.exited, 1)
        result = run("goobypls", warn=True)
        eq_(result.exited, 127)

    @raises(Failure)
    def fast_failures(self):
        run("false")

    def run_acts_as_success_boolean(self):
        ok_(not run("false", warn=True))
        ok_(run("true"))

    def non_one_return_codes_still_act_as_False(self):
        ok_(not run("goobypls", warn=True))
