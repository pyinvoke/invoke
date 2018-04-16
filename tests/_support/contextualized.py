from invoke import task


@task
def go(ctx):
    return ctx

@task
def check_warn(c):
    # default: False
    assert c.config.run.warn == True

@task
def check_pty(c):
    # default: False
    assert c.config.run.pty == True

@task
def check_hide(c):
    # default: None
    assert c.config.run.hide == 'both'

@task
def check_echo(c):
    # default: False
    assert c.config.run.echo == True
