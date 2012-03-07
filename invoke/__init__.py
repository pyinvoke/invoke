from subprocess import Popen, PIPE


__version__ = "0.1.0"


class Result(object):
    def __init__(self, stdout=None, stderr=None):
        self.stdout = stdout
        self.stderr = stderr


def run(command):
    process = Popen(command,
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE
    )
    stdout, stderr = process.communicate()
    if False:
        print "===== stdout ====="
        print stdout
        print "=================="
        print ""
        print "===== stderr ====="
        print stderr
        print "=================="
    return Result(stdout=stdout, stderr=stderr)
