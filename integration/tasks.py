"""
Tasks module for use within the integration tests.
"""

from invoke import task, contextless_task


@task
def print_foo(c):
    print("foo")

@task
def print_name(c, name):
    print(name)

@task
def print_config(c):
    print(c.foo)

@contextless_task
def print_foo_without_context():
    print("foo")

@contextless_task
def print_name_without_context(name):
    print(name)
