"""
Tasks module for use within the integration tests.
"""

from invoke import task, run


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)
