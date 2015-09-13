import operator
import os
import re
import sys
import termios
from contextlib import contextmanager
from functools import partial, wraps

from invoke.vendor.six import StringIO

from mock import patch, Mock
from spec import trap, Spec, eq_, ok_, skip

from invoke import Program, Failure
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
def sys_path(filepath=None):
    sys.path.insert(0, filepath)
    yield
    sys.path.pop(0)

support_path = partial(sys_path, filepath=support)


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


# TODO: make this part of the real API somewhere
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
def expect(invocation, out=None, err=None, program=None, invoke=True,
    test=None):
    """
    Run ``invocation`` via ``program`` and expect resulting output to match.

    May give one or both of ``out``/``err`` (but not neither).

    ``program`` defaults to ``Program()``.

    To skip automatically assuming the argv under test starts with ``"invoke
    "``, say ``invoke=False``.

    To customize the operator used for testing (default: equality), use
    ``test``.
    """
    if program is None:
        program = Program()
    if invoke:
        invocation = "invoke {0}".format(invocation)
    program.run(invocation, exit=False)
    # Perform tests
    if out is not None:
        if test:
            ok_(test(sys.stdout.getvalue(), out))
        else:
            eq_(sys.stdout.getvalue(), out)
    if err is not None:
        if test:
            ok_(test(sys.stderr.getvalue(), err))
        else:
            eq_(sys.stderr.getvalue(), err)


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


class SimpleFailure(Failure):
    """
    Failure subclass that can be raised w/o any args given.

    Useful for testing failure handling w/o having to come up with a fully
    mocked out `.Failure` & `.Result` pair each time.
    """
    def __init__(self):
        pass

    def __str__(self):
        return "SimpleFailure"

    @property
    def result(self):
        return Mock(exited=1)


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


def mock_subprocess(out='', err='', exit=0, isatty=None):
    def decorator(f):
        @wraps(f)
        @patch('invoke.runners.Popen')
        @patch('os.read')
        @patch('os.isatty')
        def wrapper(*args, **kwargs):
            args = list(args)
            Popen, read, os_isatty = args.pop(), args.pop(), args.pop()
            process = Popen.return_value
            process.returncode = exit
            process.stdout.fileno.return_value = 1
            process.stderr.fileno.return_value = 2
            # If requested, mock isatty to fake out pty detection
            if isatty is not None:
                os_isatty.return_value = isatty
            out_file = StringIO(out)
            err_file = StringIO(err)
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                return fd.read(count)
            read.side_effect = fakeread
            f(*args, **kwargs)
        return wrapper
    return decorator


def mock_pty(out='', err='', exit=0, isatty=None, trailing_error=None):
    def decorator(f):
        # Boy this is dumb. Windoooooows >:(
        ioctl_patch = lambda x: x
        if not WINDOWS:
            import fcntl
            ioctl_patch = patch('invoke.runners.fcntl.ioctl',
                wraps=fcntl.ioctl)

        @wraps(f)
        @patch('invoke.runners.pty')
        @patch('invoke.runners.os')
        @ioctl_patch
        def wrapper(*args, **kwargs):
            args = list(args)
            pty, os, ioctl = args.pop(), args.pop(), args.pop()
            # Don't actually fork, but pretend we did & that main thread is
            # also the child (pid 0) to trigger execv call; & give 'parent fd'
            # of 1 (stdout).
            pty.fork.return_value = 0, 1
            # We don't really need to care about waiting since not truly
            # forking/etc, so here we just return a nonzero "pid" + dummy value
            # (normally sent to WEXITSTATUS but we mock that anyway, so.)
            os.waitpid.return_value = None, None
            os.WEXITSTATUS.return_value = exit
            # If requested, mock isatty to fake out pty detection
            if isatty is not None:
                os.isatty.return_value = isatty
            out_file = StringIO(out)
            err_file = StringIO(err)
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                ret = fd.read(count)
                # If asked, fake a Linux-platform trailing I/O error.
                if not ret and trailing_error:
                    raise trailing_error
                return ret
            os.read.side_effect = fakeread
            f(*args, **kwargs)
            # Short-circuit if we raised an error in fakeread()
            if trailing_error:
                return
            # Sanity checks to make sure the stuff we mocked, actually got ran!
            # TODO: inject our mocks back into the tests so they can make their
            # own assertions if desired
            pty.fork.assert_called_with()
            # Test the 2nd call to ioctl; the 1st call is doing TIOGSWINSZ
            eq_(ioctl.call_args_list[1][0][1], termios.TIOCSWINSZ)
            for name in ('execv', 'waitpid', 'WEXITSTATUS'):
                assert getattr(os, name).called
        return wrapper
    return decorator
