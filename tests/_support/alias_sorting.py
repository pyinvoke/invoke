from invoke import task


@task(aliases=("z", "a"))
def toplevel(c):
    pass
