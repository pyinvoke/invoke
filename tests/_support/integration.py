from invoke.tasks import task


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)

@task
def foo():
    print("foo")

@task('foo')
def bar():
    print("bar")
