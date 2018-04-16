import logging
import os
import sys

from invoke.vendor.six import iteritems
import pytest

from _util import support


# pytest seems to tweak logging such that Invoke's debug logs go to stderr,
# which is then hella spammy if one is using --capture=no (which one must in
# order to test low level terminal IO stuff, as we do!)
# So, we explicitly turn default logging back down.
# NOTE: no real better place to put this than here
# TODO: once pytest-relaxed works with pytest 3.3, see if we can use its new
# logging functionality to remove the need for this.
logging.basicConfig(level=logging.INFO)


@pytest.fixture
def environ():
    old_environ = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(old_environ)


@pytest.fixture
def chdir_support():
    # Always do things relative to tests/_support
    os.chdir(support)
    yield
    # Chdir back to project root to avoid problems
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def clean_sys_modules():
    # TODO: _arguably_ it might be cleaner to register this as a 'finalizer'?
    # it's not like the yield isn't readable here - it's a fixture that only
    # performs teardown.
    yield
    # Strip any test-support task collections from sys.modules to prevent
    # state bleed between tests; otherwise tests can incorrectly pass
    # despite not explicitly loading/cd'ing to get the tasks they call
    # loaded.
    for name, module in iteritems(sys.modules.copy()):
        if module and support in getattr(module, '__file__', ''):
            del sys.modules[name]


@pytest.fixture
def integration(environ, chdir_support, clean_sys_modules):
    yield
