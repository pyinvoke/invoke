from invoke import task


@task(name="explicit_name")
def implicit_name(c):
    pass
