from invoke import task


@task
def no_docstring(c):
    pass


@task
def one_line(c):
    """foo
    """


@task
def two_lines(c):
    """foo
    bar
    """


@task
def leading_whitespace(c):
    """
    foo
    """


@task(aliases=("a", "b"))
def with_aliases(c):
    """foo
    """
