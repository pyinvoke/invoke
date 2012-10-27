from invoke.tasks import task


@task(default=True)
def foo():
    pass

@task(default=True)
def biz():
    pass
