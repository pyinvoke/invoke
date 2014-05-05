from invoke import task


@task
def no_docstring():
    pass

@task
def one_line():
    """foo
    """
@task
def two_lines():
    """foo
    bar
    """

@task
def leading_whitespace():
    """
    foo
    """

@task(aliases=('a', 'b'))
def with_aliases():
    """foo
    """
