from invoke.tasks import task
from invoke.runner import run


@task
def test(module=None):
    """
    Run Invoke's internal test suite.

    Say ``--module=foo``/``-m foo`` to just run ``tests/foo.py``.
    """
    base = "spec"
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else "")
    # Use pty so the spec/nose/Python process buffers "correctly"
    run(base + args, pty=True)


@task
def vendorize(package, spec, git_url=None, license=None):
    """
    Vendorize Python package ``package`` at version/SHA ``spec``.

    For Crate/PyPI releases, ``package`` should be the name of the software
    entry on those sites, and ``spec`` should be a specific version number.
    E.g. ``vendorize('lexicon', '0.1.2')``.

    For Git releases, ``package`` should be the name of the package folder
    within the checkout that needs to be vendorized and ``spec`` should be a
    Git identifier (branch, tag, SHA etc.) ``git_url`` must also be given,
    something suitable for ``git clone <git_url>``.

    For SVN releases: xxx.

    By default, no explicit license seeking is done -- we assume the license
    info is in file headers or otherwise within the Python package vendorized.
    This is not always true; specify ``license=/path/to/license/file`` to
    trigger copying of a license into the vendored folder from the
    checkout/download (relative to its root.)
    """
    # obtain intended target location
    # set real_spec to copy of spec
    # if currently occupied:
    #   nuke
    # if git_url:
    #   git clone into tempdir
    #   git checkout <spec>
    #   set target to checkout
    #   if spec does not look SHA-ish:
    #       in the checkout, obtain SHA from that branch
    #       set real_spec to that value
    # else:
    #   seek on crate for name + spec
    #   error if not available
    #   download into tempdir
    #   unpack
    #   set target to unpacked dir
    # now we have target dir:
    # * error if package dir not inside it
    # * cp -R target/package invoke/vendor/package
    # if license:
    #   cp target/$license invoke/vendor/package/
    # git commit -a -m "Update $package to $spec ($real_spec if different)"
