import os
import sys
from contextlib import contextmanager

from mock import patch
from spec import trap, Spec, eq_, skip

from invoke.platform import WINDOWS


support = os.path.join(os.path.dirname(__file__), '_support')


def skip_if_windows(fn):
    def wrapper():
        if WINDOWS:
            skip()
        return fn()
    return wrapper


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
        self.old_environ = os.environ.copy()
        os.chdir(support)

    def teardown(self):
        reset_cwd()
        os.environ.clear()
        os.environ.update(self.old_environ)


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
def _output_eq(args, stdout=None, stderr=None, code=0):
    """
    dispatch() 'args', matching output to 'std(out|err)'.

    Must give either or both of the output-expecting args.
    """
    with expect_exit(code):
        _dispatch("inv {0}".format(args))
    if stdout is not None:
        eq_(sys.stdout.getvalue(), stdout)
    if stderr is not None:
        eq_(sys.stderr.getvalue(), stderr)


@contextmanager
def expect_exit(code=0):
    """
    Run a block of code expected to sys.exit(), ignoring the exit.

    This is so we can readily test top level things like help output, listings,
    etc.
    """
    try:
        yield
    except SystemExit as e:
        if e.code != code:
            raise


@contextmanager
def run_in_configs():
    with patch('invoke.context.run') as run:
        with cd('configs'):
            yield run
