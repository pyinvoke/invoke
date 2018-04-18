from invoke import Collection

@task
def dummy(c):
    pass

ns = Collection(dummy, subcollection=Collection())
