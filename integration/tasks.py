"""
Tasks module for use within the integration tests.
"""

from invoke import task


@task
def print_foo(c):
    print("foo")


@task
def print_name(c, name):
    print(name)


@task
def print_config(c):
    print(c.foo)
