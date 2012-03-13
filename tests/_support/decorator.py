from invoke.task import task


@task(aliases=('bar',))
def foo():
    pass
