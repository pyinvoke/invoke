from invoke.tasks import task

@task
def mytask(ctx):
    pass


@task
def basic_arg(ctx, arg='val'):
    pass


@task
def multiple_args(ctx, arg1='val1', otherarg='val2'):
    pass


@task
def basic_bool(ctx, mybool=True):
    pass
