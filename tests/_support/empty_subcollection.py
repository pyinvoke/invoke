from invoke import task, Collection

@task
def dummy(c):
    pass

ns = Collection(dummy, subcollection=Collection())
