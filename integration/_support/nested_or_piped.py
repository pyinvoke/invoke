from invoke import run, ctask

@ctask
def calls_foo(c):
    c.run("inv -c nested_or_piped foo")

@ctask
def foo(c):
    c.run("echo meh")
