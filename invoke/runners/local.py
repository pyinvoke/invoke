import struct
import sys
from signal import SIGINT, SIGTERM
from subprocess import Popen, PIPE

# Base module takes care of platform-conditional imports; reuse them.
# Also reuse a few modules which get mocked in test utils.
from .base import fcntl, os, pty, termios

from .base import Runner
from ..platform import pty_size, WINDOWS
from ..util import has_fileno


class Local(Runner):
    """
    Execute a command on the local system in a subprocess.

    .. note::
        When Invoke itself is executed without a controlling terminal (e.g.
        when ``sys.stdin`` lacks a useful ``fileno``), it's not possible to
        present a handle on our PTY to local subprocesses. In such situations,
        `Local` will fallback to behaving as if ``pty=False`` (on the theory
        that degraded execution is better than none at all) as well as printing
        a warning to stderr.

        To disable this behavior, say ``fallback=False``.
    """
    def __init__(self, context):
        super(Local, self).__init__(context)
        # Bookkeeping var for pty use case
        self.status = None

    def should_use_pty(self, pty=False, fallback=True):
        use_pty = False
        if pty:
            use_pty = True
            # TODO: pass in & test in_stream, not sys.stdin
            if not has_fileno(sys.stdin) and fallback:
                if not self.warned_about_pty_fallback:
                    sys.stderr.write("WARNING: stdin has no fileno; falling back to non-pty execution!\n") # noqa
                    self.warned_about_pty_fallback = True
                use_pty = False
        return use_pty

    def read_proc_stdout(self, num_bytes):
        # Obtain useful read-some-bytes function
        if self.using_pty:
            # Need to handle spurious OSErrors on some Linux platforms.
            try:
                data = os.read(self.parent_fd, num_bytes)
            except OSError as e:
                # Only eat this specific OSError so we don't hide others
                if "Input/output error" not in str(e):
                    raise
                # The bad OSErrors happen after all expected output has
                # appeared, so we return a falsey value, which triggers the
                # "end of output" logic in code using reader functions.
                data = None
        else:
            data = os.read(self.process.stdout.fileno(), num_bytes)
        return data

    def read_proc_stderr(self, num_bytes):
        # NOTE: when using a pty, this will never be called.
        # TODO: do we ever get those OSErrors on stderr? Feels like we could?
        return os.read(self.process.stderr.fileno(), num_bytes)

    def _write_proc_stdin(self, data):
        # NOTE: parent_fd from os.fork() is a read/write pipe attached to our
        # forked process' stdout/stdin, respectively.
        fd = self.parent_fd if self.using_pty else self.process.stdin.fileno()
        # Try to write, ignoring broken pipes if encountered (implies child
        # process exited before the process piping stdin to us finished;
        # there's nothing we can do about that!)
        try:
            return os.write(fd, data)
        except OSError as e:
            if 'Broken pipe' not in str(e):
                raise

    def start(self, command, shell, env):
        if self.using_pty:
            if pty is None: # Encountered ImportError
                sys.exit("You indicated pty=True, but your platform doesn't support the 'pty' module!") # noqa
            cols, rows = pty_size()
            self.pid, self.parent_fd = pty.fork()
            # If we're the child process, load up the actual command in a
            # shell, just as subprocess does; this replaces our process - whose
            # pipes are all hooked up to the PTY - with the "real" one.
            if self.pid == 0:
                # TODO: both pty.spawn() and pexpect.spawn() do a lot of
                # setup/teardown involving tty.setraw, getrlimit, signal.
                # Ostensibly we'll want some of that eventually, but if
                # possible write tests - integration-level if necessary -
                # before adding it!
                #
                # Set pty window size based on what our own controlling
                # terminal's window size appears to be.
                # TODO: make subroutine?
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(sys.stdout.fileno(), termios.TIOCSWINSZ, winsize)
                # Use execve for bare-minimum "exec w/ variable # args + env"
                # behavior. No need for the 'p' (use PATH to find executable)
                # for now.
                # TODO: see if subprocess is using equivalent of execvp...
                os.execve(shell, [shell, '-c', command], env)
        else:
            self.process = Popen(
                command,
                shell=True,
                executable=shell,
                env=env,
                stdout=PIPE,
                stderr=PIPE,
                stdin=PIPE,
            )

    @property
    def process_is_finished(self):
        if self.using_pty:
            # NOTE:
            # https://github.com/pexpect/ptyprocess/blob/4058faa05e2940662ab6da1330aa0586c6f9cd9c/ptyprocess/ptyprocess.py#L680-L687
            # implies that Linux "requires" use of the blocking, non-WNOHANG
            # version of this call. Our testing doesn't verify this, however,
            # so...
            # NOTE: It does appear to be totally blocking on Windows, so our
            # issue #351 may be totally unsolvable there. Unclear.
            pid_val, self.status = os.waitpid(self.pid, os.WNOHANG)
            return pid_val != 0
        else:
            return self.process.poll() is not None

    def send_interrupt(self, interrupt):
        # NOTE: No need to reraise the interrupt since we have full control
        # over the local process and can kill it.
        if self.using_pty:
            os.kill(self.pid, SIGINT)
        else:
            # Use send_signal with platform-appropriate signal (Windows doesn't
            # support SIGINT unfortunately, only SIGTERM).
            # NOTE: could use subprocess.terminate() (which is cross-platform)
            # but feels best to use SIGINT as much as we possibly can as it's
            # most appropriate. terminate() always sends SIGTERM.
            # NOTE: in interactive POSIX terminals, this is technically
            # unnecessary as Ctrl-C submits the INT to the entire foreground
            # process group (which will be both Invoke and its spawned
            # subprocess). However, it doesn't seem to hurt, & ensures that a
            # *non-interactive* SIGINT is forwarded correctly.
            self.process.send_signal(SIGINT if not WINDOWS else SIGTERM)

    def returncode(self):
        if self.using_pty:
            return os.WEXITSTATUS(self.status)
        else:
            return self.process.returncode

    def stop(self):
        # No explicit close-out required (so far).
        pass
