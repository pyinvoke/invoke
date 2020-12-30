from invoke import task


@task
def go(c):
    return c


@task
def check_warn(c):
    # default: False
    assert c.config.run.warn is True


@task
def check_pty(c):
    # default: False
    assert c.config.run.pty is True


@task
def check_hide(c):
    # default: None
    assert c.config.run.hide == "both"


@task
def check_echo(c):
    # default: False
    assert c.config.run.echo is True
