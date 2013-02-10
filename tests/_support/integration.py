from invoke.tasks import task


@task
def print_foo():
    print "foo"

@task
def print_name(name):
    print name

@task('print_foo', post=['print_post'])
def print_bar():
    print "bar"

@task
def print_post():
    print "post"
