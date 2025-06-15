from invoke import task


@task
def calls_foo(c) -> None:
    c.run("inv -c nested_or_piped foo")


@task
def foo(c) -> None:
    c.run("echo meh")
