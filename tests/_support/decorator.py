from invoke.tasks import task


@task(aliases=('bar', 'otherbar'))
def foo(ctx):
    """
    Foo the bar.
    """
    pass

@task
def foo2(ctx):
    """
    Foo the bar:

      example code

    Added in 1.0
    """
    pass

@task
def foo3(ctx):
    """Foo the other bar:

      example code

    Added in 1.1
    """
    pass

@task(default=True)
def biz(ctx):
    pass

@task(help={'why': 'Motive', 'who': 'Who to punch'})
def punch(ctx, who, why):
    pass

@task(positional=['pos'])
def one_positional(ctx, pos, nonpos):
    pass

@task(positional=['pos1', 'pos2'])
def two_positionals(ctx, pos1, pos2, nonpos):
    pass

@task
def implicit_positionals(ctx, pos1, pos2, nonpos=None):
    pass

@task(optional=['myopt'])
def optional_values(ctx, myopt):
    pass
