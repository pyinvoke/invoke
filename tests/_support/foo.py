from invoke.tasks import task

@task
def mytask():
    pass


@task
def basic_arg(arg='val'):
    pass


@task
def multiple_args(arg1='val1', arg2='val2'):
    pass
