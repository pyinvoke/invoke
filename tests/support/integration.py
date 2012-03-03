from invoke import run, task


@task
def print_foo():
    print "foo"
