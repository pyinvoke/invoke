import os

from invoke import Collection, task, Exit

from invocations import ci, checks
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
    # Abort if no default shell on this system - implies some unusual dev
    # environment. Certain entirely-standalone tests will fail w/o it, even if
    # tests honoring config overrides (like the unit-test suite) don't.
    shell = c.config.global_defaults()["run"]["shell"]
    if not c.run("which {}".format(shell), hide=True, warn=True):
        err = "No {} on this system - cannot run integration tests! Try a container?"  # noqa
        raise Exit(err.format(shell))
    opts = opts or ""
    opts += " integration/"
    test(c, opts=opts, pty=pty)


@task
def coverage(c, report="term", opts="", codecov=False):
    """
    Run pytest in coverage mode. See `invocations.pytest.coverage` for details.
    """
    # Use our own test() instead of theirs.
    # Also add integration test so this always hits both.
    # (Not regression, since that's "weird" / doesn't really hit any new
    # coverage points)
    coverage_(
        c,
        report=report,
        opts=opts,
        tester=test,
        additional_testers=[integration],
        codecov=codecov,
    )


@task
def regression(c, jobs=8):
    """
    Run an expensive, hard-to-test-in-pytest run() regression checker.

    :param int jobs: Number of jobs to run, in total. Ideally num of CPUs.
    """
    os.chdir("integration/_support")
    cmd = "seq {} | parallel -n0 --halt=now,fail=1 inv -c regression check"
    c.run(cmd.format(jobs))


ns = Collection(
    test,
    coverage,
    integration,
    regression,
    vendorize,
    release,
    www,
    docs,
    sites,
    watch_docs,
    ci,
    checks.blacken,
)
ns.configure(
    {
        "blacken": {
            # Skip vendor, build dirs when blackening.
            # TODO: this is making it seem like I really do want an explicit
            # arg/conf-opt in the blacken task for "excluded paths"...ha
            "find_opts": "-and -not \( -path './invoke/vendor*' -or -path './build*' \)"  # noqa
        },
        "packaging": {
            "sign": True,
            "wheel": True,
            "check_desc": True,
            "changelog_file": os.path.join(
                www.configuration()["sphinx"]["source"], "changelog.rst"
            ),
        },
    }
)
