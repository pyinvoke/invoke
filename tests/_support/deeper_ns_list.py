from invoke import task, Collection

@task
def toplevel(ctx):
    pass

@task
def subtask(ctx):
    pass

ns = Collection(
    toplevel,
    Collection('a', subtask,
        Collection('nother', subtask)
    )
)
