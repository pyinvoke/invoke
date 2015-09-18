from invocations.docs import docs, www, sites, watch_docs
from invocations.testing import test, coverage, integration, watch_tests
from invocations.packaging import vendorize, release

from invoke import Collection
from invoke.util import LOG_FORMAT


ns = Collection(
    test, coverage, integration, vendorize, release, www, docs, sites,
    watch_docs, watch_tests
)
ns.configure({
    'tests': {
        'logformat': LOG_FORMAT,
        'package': 'invoke',
    },
})
