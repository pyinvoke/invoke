import os
import select
import sys

from .monkey import Popen, PIPE
from .exceptions import Failure, PlatformError
from .platform import WINDOWS


def normalize_hide(val):
    hide_vals = (None, False, 'out', 'stdout', 'err', 'stderr', 'both', True)
    if val not in hide_vals:
        raise ValueError("'hide' got %r which is not in %r" % (val, hide_vals,))
    if val in (None, False):
        hide = ()
    elif val in ('both', True):
        hide = ('out', 'err')
    elif val == 'stdout':
        hide = ('out',)
    elif val == 'stderr':
        hide = ('err',)
    else:
        hide = (val,)
    return hide


class Runner(object):
    """
    Abstract core command-running API.

    Actual command runners should subclass & implement the following:

    * ``run``: Command execution hooking directly into the subprocess'
      stdout/stderr pipes and returning their eventual values as distinct
      strings. Specifically, have a signature of ``def run(self, command, warn,
      hide):`` (see `.runner.run` for semantics of these) and return a 4-tuple
      of ``(stdout, stderr, exitcode, exception)``.
    * ``run_pty``: Execution utilizing a pseudo-terminal, which is then
      expected to only return a useful stdout (with stderr usually empty.) Has
      same signature and return value as ``run``.

    For an implementation example, see the source code for `.Local`.
    """
    def run(self, command, warn, hide):
        raise NotImplementedError

    def run_pty(self, command, warn, hide):
        raise NotImplementedError


class Local(Runner):
    """
    Execute a command on the local system in a subprocess.
    """
    def run(self, command, warn, hide):
        process = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            hide=hide,
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode, None

    def run_pty(self, command, warn, hide):
        # Sanity check: platforms that can't pexpect should explode usefully
        # here. (Without this, the pexpect import throws an inner
        # ImportException trying to 'import pty' which is unavailable on
        # Windows. Better to do this here than truly-fork pexpect.)
        if WINDOWS:
            err = "You seem to be on Windows, which doesn't support ptys!"
            raise PlatformError(err)
        # Proceed as normal for POSIX/etc platforms, with a runtime import
        from .vendor import pexpect

        out = []
        def out_filter(text):
            out.append(text.decode("utf-8", 'replace'))
            if 'out' not in hide:
                return text
            else:
                return b""
        p = pexpect.spawn("/bin/bash", ["-c", command])
        # Ensure pexpect doesn't barf with OSError if we fall off the end of
        # the child's input on some platforms (e.g. Linux).
        exception = None
        try:
            p.interact(output_filter=out_filter)
        except OSError as e:
            # Only capture the OSError we expect
            if "Input/output error" not in str(e):
                raise
            # Ensure it ties off the child, sets exitstatus, etc
            p.close()
            # Capture the exception in case it's NOT the OSError we think it
            # is and folks need to debug
            exception = e
        return "".join(out), "", p.exitstatus, exception


def run(command, warn=False, hide=None, pty=False, echo=False, nocolor=False,
        runner=Local):
    """
    Execute ``command`` (via ``runner``) returning a `Result` object.

    A `.Failure` exception (containing a reference to the `Result` that would
    otherwise have been returned) is raised if the command terminates with a
    nonzero return code. This behavior may be disabled by setting
    ``warn=True``.

    To disable copying the command's stdout and/or stderr to the controlling
    terminal, specify ``hide='out'`` (or ``'stdout'``), ``hide='err'`` (or
    ``'stderr'``) or ``hide='both'`` (or ``True``). The default value is
    ``None``, meaning to print everything; ``False`` will also disable hiding.

    .. note::
        Stdout and stderr are always captured and stored in the ``Result``
        object, regardless of ``hide``'s value.

    By default, ``run`` connects directly to the invoked process and reads
    its stdout/stderr streams. Some programs will buffer differently (or even
    behave differently) in this situation compared to using an actual terminal
    or pty. To use a pty, specify ``pty=True``.

    .. warning::
        Due to their nature, ptys have a single output stream, so the ability
        to tell stdout apart from stderr is **not possible** when ``pty=True``.
        As such, all output will appear on your local stdout and be captured
        into the ``stdout`` result attribute. Stderr and ``stderr`` will always
        be empty when ``pty=True``.

    `.run` does not echo the commands it runs by default; to make it do so, say
    ``echo=True``. To have echo output without color, set ``nocolor=True``.

    The ``runner`` argument allows overriding the actual execution mechanism,
    and must be a class exposing two methods, ``run`` and ``run_pty``, whose
    signatures must match ``function(command, warn, hide)`` - all of which
    match the above descriptions, re: types and default values.
    
    These methods must return a tuple of ``(stdout, stderr, exited,
    exception)``, where ``stdout`` and ``stderr`` are strings, ``exited`` is
    an integer, and ``exception`` is an exception object or ``None``.
    """
    hide = normalize_hide(hide)
    exception = False
    if echo:
        if nocolor:
            print(command)
        else:
            print("\033[1;37m%s\033[0m" % command)
    runner_ = runner()
    func = runner_.run_pty if pty else runner_.run
    stdout, stderr, exited, exception = func(command, warn, hide)
    result = Result(
        stdout=stdout,
        stderr=stderr,
        exited=exited,
        pty=pty,
        exception=exception,
    )
    if not (result or warn):
        raise Failure(result)
    return result


class Result(object):
    """
    A container for information about the result of a command execution.

    `Result` instances have the following attributes:

    * ``stdout``: The subprocess' standard output, as a multiline string.
    * ``stderr``: Same as ``stdout`` but containing standard error (unless
      the process was invoked via a pty; see `run`.)
    * ``exited``: An integer representing the subprocess' exit/return code.
    * ``return_code``: An alias to ``exited``.
    * ``ok``: A boolean equivalent to ``exited == 0``.
    * ``failed``: The inverse of ``ok``: ``True`` if the program exited with a
      nonzero return code.
    * ``pty``: A boolean describing whether the subprocess was invoked with a
      pty or not; see `run`.
    * ``exception``: Typically ``None``, but may be an exception object if
      ``pty`` was ``True`` and ``run()`` had to swallow an apparently-spurious
      ``OSError``. Solely for sanity checking/debugging purposes.

    `Result` objects' truth evaluation is equivalent to their ``ok``
    attribute's value.
    """
    # TODO: inherit from namedtuple instead? heh
    def __init__(self, stdout, stderr, exited, pty, exception=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr
        self.pty = pty
        self.exception = exception

    def __nonzero__(self):
        # Holy mismatch between name and implementation, Batman!
        return self.exited == 0

    # Python 3 ahoy
    def __bool__(self):
        return self.__nonzero__()

    def __str__(self):
        ret = ["Command exited with status %s." % self.exited]
        for x in ('stdout', 'stderr'):
            val = getattr(self, x)
            ret.append("""=== %s ===
%s
""" % (x, val.rstrip()) if val else "(no %s)" % x)
        return "\n".join(ret)

    @property
    def ok(self):
        return self.exited == 0

    @property
    def failed(self):
        return not self.ok
