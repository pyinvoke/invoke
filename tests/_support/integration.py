from invoke.tasks import task


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)

@task
def print_underscored_arg(my_option):
    print(my_option)

@task
def foo():
    print("foo")

@task(foo)
def bar():
    print("bar")

@task(foo, bar)
def biz():
    print("biz")
