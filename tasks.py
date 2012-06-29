from invoke.task import task
from invoke import run


@task
def test(module=None):
    run("spec" + ((" --tests=tests/%s.py" % module) if module else ""))
