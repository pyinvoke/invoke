"""
A semi-integration-test style fixture spanning multiple feature examples.

If we're being honest, though, the new 'tree' fixture package is a lot bigger.
"""

from invoke.tasks import task


@task
def print_foo(c):
    print("foo")


@task
def print_name(c, name):
    print(name)


@task
def print_underscored_arg(c, my_option):
    print(my_option)


@task
def foo(c):
    print("foo")


@task(foo)
def bar(c):
    print("bar")


@task
def post2(c):
    print("post2")


@task(post=[post2])
def post1(c):
    print("post1")


@task(foo, bar, post=[post1, post2])
def biz(c):
    print("biz")


@task(bar, foo, post=[post2, post1])
def boz(c):
    print("boz")
