from invoke.tasks import task


@task
def mytask(c):
    pass


@task
def basic_arg(c, arg="val"):
    pass


@task
def multiple_args(c, arg1="val1", otherarg="val2"):
    pass


@task
def basic_bool(c, mybool=True):
    pass
