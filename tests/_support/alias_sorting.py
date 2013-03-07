from invoke import task, Collection

@task(aliases=('z', 'a'))
def toplevel():
    pass
