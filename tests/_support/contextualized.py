from spec import eq_

from invoke import task


@task
def go(ctx):
    return ctx

@task
def check_warn(c):
    # default: False
    eq_(c.config.run.warn, True)

@task
def check_pty(c):
    # default: False
    eq_(c.config.run.pty, True)

@task
def check_hide(c):
    # default: None
    eq_(c.config.run.hide, 'both')

@task
def check_echo(c):
    # default: False
    eq_(c.config.run.echo, True)
