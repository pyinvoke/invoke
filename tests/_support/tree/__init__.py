from invoke import task, Collection

from . import build, deploy, provision

@task(aliases=['python'])
def shell(c):
    "Load a REPL with project state already set up."
    pass

@task
def test(c):
    "Run the test suite with baked-in args."
    pass

ns = Collection(shell, test, build, deploy, provision)
