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


@task(positional=["name"])
def print_hello(c, name="World", greeting="Hello"):
    print("{}, {}!".format(greeting, name))


@task(optional=["second"])
def print_addition(c, first, second):
    if not second:
        second = 2

    print(int(first) + int(second))
