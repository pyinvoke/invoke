from subprocess import PIPE

from .monkey import Popen
from .exceptions import Failure


__version__ = "0.1.0"


class Result(object):
    def __init__(self, stdout=None, stderr=None, exited=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr

# TODO: put this in another module?
def run(command):
    process = Popen(command,
        shell=True,
        stdout=PIPE,
        stderr=PIPE
    )
    stdout, stderr = process.communicate()
    result = Result(stdout=stdout, stderr=stderr, exited=process.returncode)
    if result.exited != 0:
        raise Failure(result)
    return result
