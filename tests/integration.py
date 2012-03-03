import os

from spec import eq_

from invoke import run


# Yea, it's not really object-oriented, but whatever :)
class Integration(object):
    # Yo dogfood, I heard you like invoking
    def basic_invocation(self):
        os.chdir(os.path.join(os.path.dirname(__file__), 'support'))
        result = run("invoke -f integration.py print_foo")
        eq_(result.stdout, "foo\n")
