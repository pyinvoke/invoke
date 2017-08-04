from invoke.tasks import task
from invoke.collection import Collection


@task
def nope(ctx):
    return "You can't see this"


@task(autoprint=True)
def yup(ctx):
    return "It's alive!"


@task(depends_on=[yup])
def dependency_check(ctx):
    pass


@task(afterwards=[yup])
def followup_check(ctx):
    pass


sub = Collection('sub', yup)
ns = Collection(nope, yup, dependency_check, followup_check, sub)
