from invoke import task

@task
def no_line():
    pass

@task
def one_line():
    """ foo
    """

@task
def second_lines():
    """ foo
    bar
    """

@task
def empty_first_line():
    """
    foo
    """

@task(aliases=('a', 'b'))
def with_aliases():
    """ foo
    """
