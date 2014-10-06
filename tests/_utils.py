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

    def teardown(self):
        reset_cwd()


def reset_cwd():
    # Chdir back to project root to avoid problems
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

@contextmanager
def cd(where):
    cwd = os.getcwd()
    os.chdir(where)
    try:
        yield
    finally:
        os.chdir(cwd)


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
    if stdout is not None:
        eq_(sys.stdout.getvalue(), stdout)
    if stderr is not None:
        eq_(sys.stderr.getvalue(), stderr)
