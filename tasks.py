import os

from invoke import Collection, task
from invoke.util import LOG_FORMAT

from invocations import travis, checks
from invocations.docs import docs, www, sites, watch_docs
from invocations.pytest import coverage as coverage_, test as test_
from invocations.packaging import vendorize, release


@task
def test(
    c,
    verbose=False,
    color=True,
    capture="no",
    module=None,
    k=None,
    x=False,
    opts="",
    pty=True,
):
    """
    Run pytest. See `invocations.pytest.test` for details.

    This is a simple wrapper around the abovementioned task, which makes a
    couple minor defaults changes appropriate for this particular test suite,
    such as:

    - setting ``capture=no`` instead of ``capture=sys``, as we do a very large
      amount of subprocess IO testing that even the ``sys``  capture screws up
    - setting ``verbose=False`` because we have a large number of tests and
      skipping verbose output by default is a ~20% time savings.)
    """
    # TODO: update test suite to use c.config.run.in_stream = False globally.
    # somehow.
    return test_(
        c,
        verbose=verbose,
        color=color,
        capture=capture,
        module=module,
        k=k,
        x=x,
        opts=opts,
        pty=pty,
    )


# TODO: replace with invocations' once the "call truly local tester" problem is
# solved (see other TODOs). For now this is just a copy/paste/modify.
@task(help=test.help)
def integration(c, opts=None, pty=True):
    """
    Run the integration test suite. May be slow!
    """
    opts = opts or ""
    opts += " integration/"
    test(c, opts=opts, pty=pty)


@task
def coverage(c, report="term", opts=""):
    """
    Run pytest in coverage mode. See `invocations.pytest.coverage` for details.
    """
    # Use our own test() instead of theirs.
    # TODO: allow coverage() to just look up the nearby-by-namespace-attachment
    # test() instead of hardcoding its own test or doing it this way with an
    # arg.
    return coverage_(c, report=report, opts=opts, tester=test)


ns = Collection(
    test,
    coverage,
    integration,
    vendorize,
    release,
    www,
    docs,
    sites,
    watch_docs,
    travis,
    checks.blacken,
)
ns.configure(
    {
        "blacken": {
            # Skip the vendor directory when blackening.
            "find_opts": "-and -not -path './invoke/vendor*'"
        },
        "tests": {"logformat": LOG_FORMAT, "package": "invoke"},
        "travis": {"sudo": {"user": "sudouser", "password": "mypass"}},
        "packaging": {
            "sign": True,
            "wheel": True,
            "check_desc": True,
            # Because of PyYAML's dual source nonsense =/
            "dual_wheels": True,
            "changelog_file": os.path.join(
                www.configuration()["sphinx"]["source"], "changelog.rst"
            ),
        },
    }
)
