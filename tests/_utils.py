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



def mock_io(patch_paths, out, err, set_mocks, teardown=None, patches=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Grab mock objects inserted by @patch, out of args.
            args = list(args)
            print >>sys.__stderr__, "args: {0!r}".format(args)
            print >>sys.__stderr__, "paths: {0!r}".format(patch_paths)
            mocks = [args.pop() for _ in patch_paths]
            # os mock is used by us & also handed to setup/teardown in case
            # they need it as well.
            mocks.append(args.pop())
            os = mocks[-1]
            print >>sys.__stderr__, "mock_io os: {0!r}".format(os)
            # Run mock setup
            set_mocks(*mocks)
            # Fake IO
            out_file = StringIO(out)
            err_file = StringIO(err)
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                return fd.read(count)
            os.read.side_effect = fakeread
            # Actual test
            f(*args, **kwargs)
            # Post-run asserts, if any
            if teardown is not None:
                teardown(*mocks)
        # Patch the OS module to mock .read
        wrapper = patch('invoke.runners.os')(wrapper)
        # @patch(...)
        for path in reversed(patch_paths):
            wrapper = patch(path)(wrapper)
        # @wraps(f)
        wrapper = wraps(f)(wrapper)
        return wrapper
    return decorator


def mock_subprocess(out='', err='', exit=0, patches=None):
    def set_mocks(Popen, os):
        process = Popen.return_value
        process.returncode = exit
        process.stdout.fileno.return_value = 1
        process.stderr.fileno.return_value = 2

    return mock_io(
        patch_paths=['invoke.runners.Popen'],
        out=out,
        err=err,
        set_mocks=set_mocks,
        patches=patches,
    )


def mock_pty(out='', err='', exit=0, patches=None):
    def set_mocks(pty, os):
        # Don't actually fork, but pretend we did & that main thread is
        # also the child (pid 0) to trigger execv call; & give 'parent fd'
        # of 1 (stdout).
        pty.fork.return_value = 0, 1
        # We don't really need to care about waiting since not truly
        # forking/etc, so here we just return a nonzero "pid" + dummy value
        # (normally sent to WEXITSTATUS but we mock that anyway, so.)
        os.waitpid.return_value = None, None
        os.WEXITSTATUS.return_value = exit

    def teardown(pty, os):
        # Sanity checks to make sure the stuff we mocked, actually got ran!
        pty.fork.assert_called_with()
        for name in ('execv', 'waitpid', 'WEXITSTATUS'):
            assert getattr(os, name).called

    wat = mock_io(
        patch_paths=['invoke.runners.pty'],
        out=out,
        err=err,
        set_mocks=set_mocks,
        teardown=teardown,
        patches=patches
    )
    return wat
