from invoke.task import task
from invoke import run


@task
def foo():
    print "Hm"
