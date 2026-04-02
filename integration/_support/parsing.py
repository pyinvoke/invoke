from invoke import task
from invoke.context import Context


@task(optional=["meh"])
def foo(c: Context, meh: bool = False) -> None:
    print(meh)


@task
def use_remainder(c: Context, known: str, optional: bool = False) -> None:
    print(f"{known=}, {optional=}, remainder={c.remainder!r}")
