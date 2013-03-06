from invocations import docs
from invocations.testing import test
from invocations.packaging import vendorize, release

from invoke import task, run, Collection


@task
def doctree():
    run("tree -Ca -I \".git|*.pyc|*.swp|dist|*.egg-info|_static|_build\" docs")

docs = Collection.from_module(docs)
docs.add_task(doctree, 'tree')
ns = Collection(test, vendorize, release, docs)
