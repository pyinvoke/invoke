from invoke.tasks import task


@task
def foo(c):
    print("Hm")


@task
def noop(c):
    pass
