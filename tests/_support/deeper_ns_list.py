from invoke import task, Collection

@task
def toplevel():
    pass

@task
def subtask():
    pass

ns = Collection(
    toplevel,
    Collection('a', subtask,
        Collection('nother', subtask)
    )
)
