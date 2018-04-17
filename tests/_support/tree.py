from invoke import task, Collection

@task
def tip_toplevel(ctx):
    """
    This is tip-toplevel's docstring.

    And this is its second line.
    """
    pass

@task
def second_toplevel(ctx):
    """
    This is second-toplevel's docstring.

    And this? Its second line.
    """
    pass

@task
def subtask(ctx):
    """
    This is subtask's docstring.

    And this is another line.
    """
    pass

@task
def nother_subtask(ctx):
    """
    This is nother-subtask's docstring.

    And this is yet another line.
    """
    pass

@task
def sub_subtask(c):
    """
    This is sub-subtask's docstring.

    Christ.
    """
    pass

@task
def yellow_subtask(c):
    """
    We all live in an etc
    """
    pass

@task
def serious(c):
    """
    Srs
    """
    pass

@task
def business(c):
    """
    Bzns
    """
    pass

ns = Collection(
    tip_toplevel,
    second_toplevel,
    Collection('a', subtask, nother_subtask,
        Collection('deeper', sub_subtask, yellow_subtask)),
    Collection('less-cutesy', serious, business))
