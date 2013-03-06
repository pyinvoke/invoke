from invoke import task, Collection


@task
def top_level():
    pass

@task
def sub_task():
    pass

sub = Collection('sub', sub_task)
ns = Collection(top_level, sub)
