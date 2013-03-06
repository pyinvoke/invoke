from invoke import task, Collection


@task(aliases=['othertop'])
def top_level():
    pass

@task(aliases=['othersub'])
def sub_task():
    pass

sub = Collection('sub', sub_task)
ns = Collection(top_level, sub)
