from invoke import task
from invoke.util import debug


@task
def foo(ctx):
    debug("my-sentinel")
