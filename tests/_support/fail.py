from invoke.tasks import task
from invoke.runner import run

@task
def fail():
    run("false")
