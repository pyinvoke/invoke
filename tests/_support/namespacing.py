from invoke import Collection, task, call

from subspace import module


@task
def top_pre(c):
    pass


@task(call(top_pre))
def toplevel(c):
    pass


ns = Collection(module, toplevel)
