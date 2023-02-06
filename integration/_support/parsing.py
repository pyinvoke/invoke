from invoke import task


@task(optional=["meh"])
def foo(c: object, meh: bool = False) -> None:
    print(meh)
