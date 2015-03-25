from invoke import ctask


@ctask
def go(ctx):
    return ctx


@ctask
def run(ctx):
    ctx.run('false')
