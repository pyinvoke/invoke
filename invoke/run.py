import os
import pty
import select
import sys
from subprocess import Popen
import pexpect

from .exceptions import Failure


class Result(object):
    """
    A container for information about the result of a command execution.

    `Result`s have the following attributes:

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
    """
    def __init__(self, stdout=None, stderr=None, exited=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr

    def __nonzero__(self):
        # Holy mismatch between name and implementation, Batman!
        return self.exited == 0

    def __str__(self):
        ret = ["Command exited with status %s." % self.exited]
        for x in ('stdout', 'stderr'):
            val = getattr(self, x)
            ret.append("""=== %s ===
%s
""" % (x, val.rstrip()) if val else "(no %s)" % x)
        return "\n".join(ret)


def normalize_hide(val):
    hide_vals = (None, 'out', 'err', 'both')
    if val not in hide_vals:
        raise ValueError("'hide' kwarg must be one of %r" % (hide_vals,))
    if val is None:
        hide = ()
    elif val is 'both':
        hide = ('out', 'err')
    else:
        hide = (val,)
    return hide


def run(command, warn=False, hide=None, pty=False):
    """
    Execute ``command`` in a local subprocess, returning a `Result` object.

    A `Failure` exception (which contains a reference to the `Result` that
    would otherwise have been returned) is raised if the subprocess terminates
    with a nonzero return code. This behavior may be disabled by setting
    ``warn=True``.

    To disable copying the subprocess' stdout and/or stderr to the controlling
    terminal, specify ``hide='out'``, ``hide='err'`` or ``hide='both'``. (The
    default value is ``None``, meaning to print everything.)

    .. note::
        Stdout and stderr are always captured and stored in the ``Result``
        object, regardless of ``hide``'s value.

    By default, ``run`` connects directly to the invoked subprocess and reads
    its stdout/stderr streams. Some programs will buffer differently (or even
    behave differently) in this situation compared to using an actual terminal
    or pty. To use a pty, specify ``pty=True``.

    .. warn::
        Due to their nature, ptys have a single output stream, so the ability
        to tell stdout apart from stderr is **not possible** when ``pty=True``.
        As such, all output will appear on your local stdout and be captured
        into the ``stdout`` result attribute. Stderr and ``stderr`` will always
        be empty when ``pty=True``.
    """
    parent, child = pty.openpty()
    # TODO: branch, using PIPE + communicate(), if distinct stderr desired &
    # interactivity not required. (You cannot have both.)
    # TODO: that requires using custom hide-enabled Popen subclass.
    process = Popen(command,
        shell=True,
        stdout=child,
        stderr=child,
        close_fds=True,
    )
    stdout = []
    stderr = []
    # Attempt reading until we read EOF, regardless of exit code status.
    while True:
        rlist, wlist, xlist = select.select([parent], [], [parent], 0.01)
        if parent in rlist:
            data = os.read(parent, 1)
            if data == "":
                os.close(parent)
            if hide is None:
                sys.stdout.write(data)
            stdout.append(data)
        else:
            # Here, we are unable to read (implying the child process has no
            # more output for us) AND the return code has been "filed" with
            # subprocess (implying the child process is not only not printing
            # anything, but has terminated.)
            if process.poll() is not None:
                break
    # Can't read any more; wait for exit code.
    exitcode = process.wait()
    result = Result(stdout="".join(stdout), stderr="".join(stderr), exited=exitcode)
    if not (result or warn):
        raise Failure(result)
    return result
