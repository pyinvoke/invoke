from invoke.tasks import task


@task
def print_foo(ctx):
    print("foo")

@task
def print_name(ctx, name):
    print(name)

@task
def print_underscored_arg(ctx, my_option):
    print(my_option)

@task
def foo(ctx):
    print("foo")

@task(foo)
def bar(ctx):
    print("bar")

@task
def post2(ctx):
    print("post2")

@task(post=[post2])
def post1(ctx):
    print("post1")

@task(foo, bar, post=[post1, post2])
def biz(ctx):
    print("biz")

@task(bar, foo, post=[post2, post1])
def boz(ctx):
    print("boz")
