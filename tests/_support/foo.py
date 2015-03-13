from invoke.tasks import task

@task
def mytask():
    pass


@task
def basic_arg(arg='val'):
    pass
