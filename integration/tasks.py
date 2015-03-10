"""
Tasks module for use within the integration tests.
"""

from invoke import task, ctask


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)

@ctask
def print_config(c):
    print(c.foo)
