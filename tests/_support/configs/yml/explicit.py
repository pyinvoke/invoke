from invoke import task, Collection


@task
def mytask(c):
    assert c.outer.inner.hooray == "yml"


ns = Collection(mytask)
