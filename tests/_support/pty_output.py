from invoke.task import task
from invoke.run import run


cmd = "echo foo && ./err bar"


def _go(hide):
    run(cmd, hide=hide, pty=True)

@task
def hide_out():
    _go('out')

@task
def hide_err():
    _go('err')

@task
def hide_both():
    _go('both')
