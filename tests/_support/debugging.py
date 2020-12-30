from invoke import task
from invoke.util import debug


@task
def foo(c):
    debug("my-sentinel")
