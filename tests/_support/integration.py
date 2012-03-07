from invoke import run
from invoke.task import task


@task
def print_foo():
    print "foo"
