from invoke import Config, task


@task
def calls_foo(c: Config) -> None:
    c.run("inv -c nested_or_piped foo")


@task
def foo(c: Config) -> None:
    c.run("echo meh")
