from invoke import Collection, task, call

from package import module

@task
def top_pre(ctx):
    pass

@task(call(top_pre))
def toplevel(ctx):
    pass

ns = Collection(module, toplevel)
