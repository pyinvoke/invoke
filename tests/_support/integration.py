from invoke.tasks import task


@task
def print_foo():
    print "foo"

@task
def print_name(name):
    print name

@task('print_foo')
def print_bar():
    print "bar"
