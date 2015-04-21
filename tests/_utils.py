import os
import re
import sys
from contextlib import contextmanager
from functools import partial, wraps
from invoke.vendor.six import StringIO

from mock import patch
from spec import trap, Spec, eq_, skip

from invoke.platform import WINDOWS


support = os.path.join(os.path.dirname(__file__), '_support')


def skip_if_windows(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if WINDOWS:
            skip()
        return fn(*args, **kwargs)
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
def mocked_run():
    with patch('invoke.runners.Runner.run') as run:
        yield run


def _assert_contains(haystack, needle, invert):
    matched = re.search(needle, haystack, re.M)
    if (invert and matched) or (not invert and not matched):
        raise AssertionError("r'%s' %sfound in '%s'" % (
            needle,
            "" if invert else "not ",
            haystack
        ))

assert_contains = partial(_assert_contains, invert=False)
assert_not_contains = partial(_assert_contains, invert=True)


def mock_subprocess(out='', err='', exit=0):
    def decorator(f):
        @wraps(f)
        @patch('invoke.runners.Popen')
        @patch('os.read')
        def wrapper(*args, **kwargs):
            args = list(args)
            Popen, read = args.pop(), args.pop()
            process = Popen.return_value
            process.returncode = exit
            process.stdout.fileno.return_value = 1
            process.stderr.fileno.return_value = 2
            out_file = StringIO(out)
            err_file = StringIO(err)
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                return fd.read(count)
            read.side_effect = fakeread
            f(*args, **kwargs)
        return wrapper
    return decorator
