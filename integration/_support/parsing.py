from invoke import task


@task(optional=["meh"])
def foo(c, meh=False) -> None:
    print(meh)
