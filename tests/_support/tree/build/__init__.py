"Tasks for compiling static code and assets."

from invoke import task, Collection

from . import docs, python

@task(name='all', aliases=['everything'], default=True)
def all_(c):
    "Build all necessary artifacts."
    pass

@task(aliases=['extension'])
def ext(c):
    "Build our internal C extension."
    pass

ns = Collection(all_, ext, docs, python) 
