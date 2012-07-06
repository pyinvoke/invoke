from invoke.task import task
from invoke.run import run

@task
def fail():
    run("false")
