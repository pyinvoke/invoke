from subprocess import PIPE
from .monkey import Popen


__version__ = "0.1.0"


class Result(object):
    def __init__(self, stdout=None, stderr=None):
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
    return Result(stdout=stdout, stderr=stderr)
