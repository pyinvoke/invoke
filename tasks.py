import sys
import time

from invocations.docs import docs, www, sites, watch_docs
from invocations.testing import test, coverage, integration
from invocations.packaging import vendorize, release

from invoke import ctask as task, Collection, Context
from invoke.util import LOG_FORMAT


@task
def watch_tests(c, module=None):
    """
    Watch source tree and test tree for changes, rerunning tests as necessary.
    """
    watch(
        c, test, ['\./invoke/', '\./tests/'], ['.*/\..*\.swp'], module=module
    )


ns = Collection(
    test, coverage, integration, vendorize, release, www, docs, sites,
    watch_docs, watch_tests
)
ns.configure({
    'coverage': {'package': 'invoke'},
    'tests': {'logformat': LOG_FORMAT},
})
