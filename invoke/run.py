from subprocess import PIPE

from .monkey import Popen
from .exceptions import Failure


class Result(object):
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

def run(command, warn=False, hide=None):
    """
    Execute ``command`` in a local subprocess.

    By default, raises an exception if the subprocess terminates with a nonzero
    return code. This may be disabled by setting ``warn=True``.

    To disable printing the subprocess' stdout and/or stderr to the controlling
    terminal, specify ``hide='out'``, ``hide='err'`` or ``hide='both'``. (The
    default value is ``None``, meaning to print everything.)

    .. note::
        The stdout and stderr are always captured and stored in the result
        object, regardless of this setting's value.
    """
    process = Popen(command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE,
        hide=normalize_hide(hide)
    )
    stdout, stderr = process.communicate()
    result = Result(stdout=stdout, stderr=stderr, exited=process.returncode)
    if not (result or warn):
        raise Failure(result)
    return result
