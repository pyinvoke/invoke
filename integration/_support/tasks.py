"""
Tasks module for use within the integration tests.
"""

from invoke import Config, task


@task
def print_foo(c: object) -> None:
    print("foo")


@task
def print_name(c: object, name: object) -> None:
    print(name)


@task
def print_config(c: Config) -> None:
    print(c.foo)
