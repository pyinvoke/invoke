from invoke.tasks import task


@task
def nope():
    return "You can't see this"


@task(autoprint=True)
def yup():
    return "It's alive!"
