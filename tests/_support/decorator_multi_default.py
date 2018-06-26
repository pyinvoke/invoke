from invoke.tasks import task


@task(default=True)
def foo(c):
    pass


@task(default=True)
def biz(c):
    pass
