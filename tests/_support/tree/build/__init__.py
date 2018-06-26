"Tasks for compiling static code and assets."

from invoke import task, Collection

from . import docs, python


@task(name="all", aliases=["everything"], default=True)
def all_(c):
    "Build all necessary artifacts."
    pass


@task(aliases=["ext"])
def c_ext(c):
    "Build our internal C extension."
    pass


@task
def zap(c):
    "A silly way to clean."
    pass


ns = Collection(all_, c_ext, zap, docs, python)
