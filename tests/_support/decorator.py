from invoke.task import task


@task(aliases=('bar',))
def foo():
    pass

@task(default=True)
def biz():
    pass

@task(help={'why': 'Motive'})
def punch(who, why):
    pass
