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

@task(post=[post2])
def post1():
    print("post1")

@task
def post2():
    print("post2")

@task(foo, bar, post=[post1, post2])
def biz():
    print("biz")

@task(bar, foo, post=[post2, post1])
def boz():
    print("boz")
