from invoke import task, Collection

from . import build, deploy, provision

@task(aliases=['ipython'])
def shell(c):
    "Load a REPL with project state already set up."
    pass

@task(aliases=['run_tests'])
def test(c):
    "Run the test suite with baked-in args."
    pass

ns = Collection(shell, test, build, deploy, provision)
