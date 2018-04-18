"Tasks for compiling static code and assets."

from invoke import task, Collection

from . import docs, python

@task(name='all', aliases=['everything'], default=True)
def all_(c):
    "Build all necessary artifacts."
    pass

@task(aliases=['ext'])
def c_ext(c):
    "Build our internal C extension."
    pass

ns = Collection(all_, c_ext, docs, python)
