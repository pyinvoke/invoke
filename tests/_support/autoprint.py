from invoke.tasks import task
from invoke.collection import Collection


@task
def nope(c):
    return "You can't see this"


@task(autoprint=True)
def yup(c):
    return "It's alive!"


@task(pre=[yup])
def pre_check(c):
    pass


@task(post=[yup])
def post_check(c):
    pass


sub = Collection("sub", yup)
ns = Collection(nope, yup, pre_check, post_check, sub)
