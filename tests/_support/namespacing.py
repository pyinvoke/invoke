from invoke import Collection, task, call

from package import module

@task
def top_pre():
    pass

@task(call(top_pre))
def toplevel():
    pass

ns = Collection(module, toplevel)
