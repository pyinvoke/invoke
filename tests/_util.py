import os
import sys
try:
    import termios
except ImportError:
    # Not available on Windows
    termios = None
from contextlib import contextmanager
from functools import wraps

from invoke.vendor.six import BytesIO, b

from mock import patch, Mock
from spec import trap, Spec, eq_, skip

from invoke import Program, UnexpectedExit, Runner
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
    try:
        yield
    finally:
        sys.path.pop(0)


def load(name):
    with support_path():
        return __import__(name)


class IntegrationSpec(Spec):
    def setup(self):
        self.old_environ = os.environ.copy()
        os.chdir(support)

    def teardown(self):
        # Chdir back to project root to avoid problems
        os.chdir(os.path.join(os.path.dirname(__file__), '..'))
        # Nuke changes to environ
        os.environ.clear()
        os.environ.update(self.old_environ)


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
    ``test`` (which should be an assertion wrapper of some kind).
    """
    if program is None:
        program = Program()
    if invoke:
        invocation = "invoke {0}".format(invocation)
    program.run(invocation, exit=False)
    # Perform tests
    if out is not None:
        (test or eq_)(sys.stdout.getvalue(), out)
    if err is not None:
        (test or eq_)(sys.stderr.getvalue(), err)


class SimpleFailure(UnexpectedExit):
    """
    UnexpectedExit subclass that can be raised w/o any args given.

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


def mock_subprocess(out='', err='', exit=0, isatty=None, insert_Popen=False):
    def decorator(f):
        @wraps(f)
        @patch('invoke.runners.Popen')
        @patch('os.read')
        @patch('sys.stdin', new_callable=BytesIO)
        def wrapper(*args, **kwargs):
            args = list(args)
            Popen, read, sys_stdin = args.pop(), args.pop(), args.pop()
            process = Popen.return_value
            process.returncode = exit
            process.stdout.fileno.return_value = 1
            process.stderr.fileno.return_value = 2
            # If requested, mock isatty to fake out pty detection
            if isatty is not None:
                sys_stdin.isatty = Mock(return_value=isatty)
            out_file = BytesIO(b(out))
            err_file = BytesIO(b(err))
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                return fd.read(count)
            read.side_effect = fakeread
            if insert_Popen:
                args.append(Popen)
            f(*args, **kwargs)
        return wrapper
    return decorator


def mock_pty(out='', err='', exit=0, isatty=None, trailing_error=None,
    skip_asserts=False, insert_os=False):
    # Windows doesn't have ptys, so all the pty tests should be
    # skipped anyway...
    if WINDOWS:
        return skip_if_windows

    def decorator(f):
        import fcntl
        ioctl_patch = patch('invoke.runners.fcntl.ioctl', wraps=fcntl.ioctl)

        @wraps(f)
        @patch('invoke.runners.pty')
        @patch('invoke.runners.os')
        @ioctl_patch
        def wrapper(*args, **kwargs):
            args = list(args)
            pty, os, ioctl = args.pop(), args.pop(), args.pop()
            # Don't actually fork, but pretend we did & that main thread is
            # also the child (pid 0) to trigger execve call; & give 'parent fd'
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
            out_file = BytesIO(b(out))
            err_file = BytesIO(b(err))
            def fakeread(fileno, count):
                fd = {1: out_file, 2: err_file}[fileno]
                ret = fd.read(count)
                # If asked, fake a Linux-platform trailing I/O error.
                if not ret and trailing_error:
                    raise trailing_error
                return ret
            os.read.side_effect = fakeread
            if insert_os:
                args.append(os)
            f(*args, **kwargs)
            # Short-circuit if we raised an error in fakeread()
            if trailing_error:
                return
            # Sanity checks to make sure the stuff we mocked, actually got ran!
            # TODO: inject our mocks back into the tests so they can make their
            # own assertions if desired
            pty.fork.assert_called_with()
            # Expect a get, and then later set, of terminal window size
            eq_(ioctl.call_args_list[0][0][1], termios.TIOCGWINSZ)
            eq_(ioctl.call_args_list[1][0][1], termios.TIOCSWINSZ)
            if not skip_asserts:
                for name in ('execve', 'waitpid', 'WEXITSTATUS'):
                    assert getattr(os, name).called
        return wrapper
    return decorator


class _Dummy(Runner):
    """
    Dummy runner subclass that does minimum work required to execute run().

    It also serves as a convenient basic API checker; failure to update it to
    match the current Runner API will cause TypeErrors, NotImplementedErrors,
    and similar.
    """
    # Neuter the input loop sleep, so tests aren't slow (at the expense of CPU,
    # which isn't a problem for testing).
    input_sleep = 0

    def start(self, command, shell, env):
        pass

    def read_proc_stdout(self, num_bytes):
        return ""

    def read_proc_stderr(self, num_bytes):
        return ""

    def _write_proc_stdin(self, data):
        pass

    @property
    def process_is_finished(self):
        return True

    def returncode(self):
        return 0

    def send_interrupt(self, exception):
        pass

    def stop(self):
        pass


# Dummy command that will blow up if it ever truly hits a real shell.
_ = "nope"


# Runner that fakes ^C during subprocess exec
class _KeyboardInterruptingRunner(_Dummy):
    def wait(self):
        raise KeyboardInterrupt


class OhNoz(Exception):
    pass
