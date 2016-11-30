from invoke import task, Collection


@task(aliases=['othertop'])
def top_level(ctx):
    pass

@task(aliases=['othersub'], default=True)
def sub_task(ctx):
    pass

sub = Collection('sub', sub_task)
ns = Collection(top_level, sub)
