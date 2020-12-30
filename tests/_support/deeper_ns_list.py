from invoke import task, Collection


@task
def toplevel(c):
    pass


@task
def subtask(c):
    pass


ns = Collection(
    toplevel, Collection("a", subtask, Collection("nother", subtask))
)
