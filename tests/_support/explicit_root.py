from invoke import task, Collection


@task(aliases=['other_top'])
def top_level(ctx):
    pass

@task(aliases=['other_sub'], default=True)
def sub_task(ctx):
    pass

sub = Collection('sub_level', sub_task)
ns = Collection(top_level, sub)
