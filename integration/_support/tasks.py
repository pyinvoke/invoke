"""
Tasks module for use within the integration tests.
"""

from invoke import task


@task
def print_foo(c) -> None:
    print("foo")


@task
def print_name(c, name) -> None:
    print(name)


@task
def print_config(c) -> None:
    print(c.foo)
