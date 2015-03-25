from invoke import run
from invoke.tasks import task


@task
def simple():
    run("false")

@task(positional=['pos'])
def missing_pos(pos):
    pass
