from invoke import task, Collection

@task
def z_toplevel(ctx):
    pass

@task
def subtask(ctx):
    pass

ns = Collection(z_toplevel, Collection('a', Collection('b', subtask)))
