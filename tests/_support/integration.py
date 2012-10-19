from invoke.task import task


@task
def print_foo():
    print "foo"

@task(positional=[])
def print_name(name):
    print name
