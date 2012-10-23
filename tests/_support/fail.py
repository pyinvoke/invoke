from invoke.tasks import task
from invoke.runner import run

@task
def simple():
    run("false")

@task(positional=['pos'])
def missing_pos(pos):
    pass
