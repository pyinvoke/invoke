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
def followup2(ctx):
    print("followup2")

@task(afterwards=[followup2])
def followup1(ctx):
    print("followup1")

@task(depends_on=[foo, bar], afterwards=[followup1, followup2])
def biz(ctx):
    print("biz")

@task(depends_on=[bar, foo], afterwards=[followup2, followup1])
def boz(ctx):
    print("boz")
