from invoke import task


@task
def no_docstring(ctx):
    pass

@task
def task_one(ctx):
    """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam id dictum

    risus. Nulla lorem justo, sagittis in volutpat eget
    """

@task
def task_two(ctx):
    """
    Nulla eget ultrices ante. Curabitur sagittis commodo posuere. Duis dapibus

    facilisis, lacus et dapibus rutrum, lectus turpis egestas dui
    """
