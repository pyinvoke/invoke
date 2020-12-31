from invoke.tasks import task


@task(aliases=("bar", "otherbar"))
def foo(c):
    """
    Foo the bar.
    """
    pass


@task
def foo2(c):
    """
    Foo the bar:

      example code

    Added in 1.0
    """
    pass


@task
def foo3(c):
    """Foo the other bar:

      example code

    Added in 1.1
    """
    pass


@task(default=True)
def biz(c):
    pass


@task(help={"why": "Motive", "who": "Who to punch"})
def punch(c, who, why):
    pass


@task(positional=["pos"])
def one_positional(c, pos, nonpos):
    pass


@task(positional=["pos1", "pos2"])
def two_positionals(c, pos1, pos2, nonpos):
    pass


@task
def implicit_positionals(c, pos1, pos2, nonpos=None):
    pass


@task(optional=["myopt"])
def optional_values(c, myopt):
    pass


@task(iterable=["mylist"])
def iterable_values(c, mylist=None):
    pass


@task(incrementable=["verbose"])
def incrementable_values(c, verbose=None):
    pass
