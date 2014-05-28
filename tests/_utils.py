import os, sys
from contextlib import contextmanager

from spec import trap, Spec, eq_
from mock import patch


support = os.path.join(os.path.dirname(__file__), '_support')

@contextmanager
def support_path():
    sys.path.insert(0, support)
    yield
    sys.path.pop(0)

def load(name):
    with support_path():
        return __import__(name)


class IntegrationSpec(Spec):
    def setup(self):
        os.chdir(support)
        # Set up a patched sys.exit if not already patched.
        # (spec() will run both setup() >1 time on nested classes.)
        # TODO: fix that.
        if not hasattr(self, 'sys_exit'):
            self.sys_exit = patch('sys.exit').start()

    def teardown(self):
        patch.stopall()


# Strings are easier to type & read than lists

def _dispatch(argstr, version=None):
    from invoke.cli import dispatch
    return dispatch(argstr.split(), version)

@trap
def _output_eq(args, stdout=None, stderr=None):
    """
    dispatch() 'args', matching output to 'std(out|err)'.

    Must give either or both of the output-expecting args.
    """
    _dispatch("inv {0}".format(args))
    if stdout:
        eq_(sys.stdout.getvalue(), stdout)
    if stderr:
        eq_(sys.stderr.getvalue(), stderr)
