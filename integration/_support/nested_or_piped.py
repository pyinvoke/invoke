from invoke import task

@task
def calls_foo(c):
    c.run("inv -c nested_or_piped foo")

@task
def foo(c):
    c.run("echo meh")
