from invocations.docs import clean_docs, browse_docs, docs
from invocations.testing import test
from invocations.packaging import vendorize, release

from invoke import task, run


@task
def doctree():
    run("tree -Ca -I \".git|*.pyc|*.swp|dist|*.egg-info|_static|_build\" docs")
