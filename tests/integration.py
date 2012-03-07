import os

from spec import eq_

from invoke import run

from _utils import support


# Yea, it's not really object-oriented, but whatever :)
class Integration(object):
    # Yo dogfood, I heard you like invoking
    def basic_invocation(self):
        os.chdir(support)
        result = run("invoke -c integration print_foo")
        eq_(result.stdout, "foo\n")
