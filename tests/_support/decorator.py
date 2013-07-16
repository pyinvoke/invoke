from invoke.tasks import task


@task(aliases=('bar', 'otherbar'))
def foo():
    pass

@task(default=True)
def biz():
    pass

@task(help={'why': 'Motive', 'who': 'Who to punch'})
def punch(who, why):
    pass

@task(positional=['pos'])
def one_positional(pos, nonpos):
    pass

@task(positional=['pos1', 'pos2'])
def two_positionals(pos1, pos2, nonpos):
    pass

@task
def implicit_positionals(pos1, pos2, nonpos=None):
    pass
