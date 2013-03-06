from invoke import Collection, task

from package import module

@task
def toplevel():
    pass

ns = Collection(module, toplevel)
