from invoke.tasks import task
from invoke.runner import run

@task
def simple():
    run("false")
