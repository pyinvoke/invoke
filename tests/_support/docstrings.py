from invoke import task


@task
def no_docstring(ctx):
    pass

@task
def one_line(ctx):
    """foo
    """
@task
def two_lines(ctx):
    """foo
    bar
    """

@task
def leading_whitespace(ctx):
    """
    foo
    """

@task(aliases=('a', 'b'))
def with_aliases(ctx):
    """foo
    """
