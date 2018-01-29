from invoke import task


@task(optional=['meh'])
def foo(c, meh=False):
    print(meh)
