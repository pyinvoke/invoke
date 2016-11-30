from invoke.tasks import task


@task(default=True)
def foo(ctx):
    pass

@task(default=True)
def biz(ctx):
    pass
