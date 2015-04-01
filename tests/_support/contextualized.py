from spec import eq_

from invoke import ctask


@ctask
def go(ctx):
    return ctx

@ctask
def check_warn(c):
    # default: False
    eq_(c.config.run.warn, True)

@ctask
def check_pty(c):
    # default: False
    eq_(c.config.run.pty, True)

@ctask
def check_hide(c):
    # default: None
    eq_(c.config.run.hide, 'both')

@ctask
def check_echo(c):
    # default: False
    eq_(c.config.run.echo, True)
