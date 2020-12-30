from invoke import task, Collection


@task
def z_toplevel(c):
    pass


@task
def subtask(c):
    pass


ns = Collection(z_toplevel, Collection("a", Collection("b", subtask)))
