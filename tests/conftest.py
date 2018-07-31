import logging
import os
import sys
import termios

from invoke.vendor.six import iteritems
import pytest
from mock import patch

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
def reset_environ():
    """
    Resets `os.environ` to its prior state after the fixtured test finishes.
    """
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
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))


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
        # Get some comparable __file__ path value, including handling cases
        # where it is None instead of undefined (seems new in Python 3.7?)
        if module and support in (getattr(module, "__file__", "") or ""):
            del sys.modules[name]


@pytest.fixture
def integration(reset_environ, chdir_support, clean_sys_modules):
    yield


@pytest.fixture
def mock_termios():
    with patch("invoke.terminals.termios") as mocked:
        # Ensure mocked termios has 'real' values for constants...otherwise
        # doing bit arithmetic on Mocks kinda defeats the point.
        mocked.ECHO = termios.ECHO
        mocked.ICANON = termios.ICANON
        mocked.VMIN = termios.VMIN
        mocked.VTIME = termios.VTIME
        yield mocked
