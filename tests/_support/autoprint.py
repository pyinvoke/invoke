from invoke.tasks import task


@task
def nope():
    return "You can't see this"


@task(autoprint=True)
def yup():
    return "It's alive!"


@task(pre=[yup])
def pre_check():
    pass


@task(post=[yup])
def post_check():
    pass
