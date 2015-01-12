from invoke import task, Collection

@task
def z_toplevel():
    pass

@task
def subtask():
    pass

ns = Collection(z_toplevel, Collection('a', Collection('b', subtask)))
