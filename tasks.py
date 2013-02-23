from invocations.docs import clean_docs, browse_docs, docs as docs_, api_docs
from invocations.testing import test
from invocations.packaging import vendorize, release

from invoke import task, run


@task
def doctree():
    run("tree -Ca -I \".git|*.pyc|*.swp|dist|*.egg-info|_static|_build\" docs")

# TODO: allow importing upstream 'docs' in non-binding fashion
# TODO: before/after hooks
@task
def docs(clean=False, browse=False):
    # Override clean to apply to API docs too
    api_docs.body(target='invoke', exclude='invoke/vendor')
    docs_.body(clean=clean, browse=browse)
