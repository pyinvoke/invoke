from subprocess import PIPE

from .monkey import Popen
from .exceptions import Failure


__version__ = "0.1.0"


class Result(object):
    def __init__(self, stdout=None, stderr=None, exited=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr

    def __nonzero__(self):
        # Holy mismatch between name and implementation, Batman!
        return self.exited == 0


# TODO: put this in another module?
def run(command, warn=False):
    """
    Execute ``command`` in a local subprocess.

    By default, raises an exception if the subprocess terminates with a nonzero
    return code. This may be disabled by setting ``warn=True``.
    """
    process = Popen(command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE
    )
    stdout, stderr = process.communicate()
    result = Result(stdout=stdout, stderr=stderr, exited=process.returncode)
    if not (result or warn):
        raise Failure(result)
    return result
