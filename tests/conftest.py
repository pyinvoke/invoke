import logging
import os
import sys
import termios

import pytest
from unittest.mock import patch

from _util import support

# Set up icecream globally for convenience.
from icecream import install
install()


# pytest seems to tweak logging such that Invoke's debug logs go to stderr,
# which is then hella spammy if one is using --capture=no (which one must in
# order to test low level terminal IO stuff, as we do!)
# So, we explicitly turn default logging back down.
# NOTE: no real better place to put this than here
# TODO: see if we can use modern pytest's logging functionality to remove the
# need for this, now that pytest-relaxed was modernized
logging.basicConfig(level=logging.INFO)


@pytest.fixture(autouse=True)
def fake_user_home():
    # Ignore any real user homedir for purpose of testing.
    # This allows, for example, a user who has real Invoke configs in their
    # homedir to still run the test suite safely.
    # TODO: this is still a bit of a kludge & doesn't solve systemwide configs
    with patch("invoke.config.expanduser", side_effect=lambda x: x):
        yield


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
    """
    Attempt to nix any imports incurred by the test, to prevent state bleed.

    In some cases this prevents outright errors (eg a test accidentally relying
    on another's import of a task tree in the support folder) and in others
    it's required because we're literally testing runtime imports.
    """
    snapshot = sys.modules.copy()
    yield
    # Iterate over another copy to avoid ye olde mutate-during-iterate problem
    # NOTE: cannot simply 'sys.modules = snapshot' as that is warned against
    for name, module in sys.modules.copy().items():
        # Delete anything newly added (imported)
        if name not in snapshot:
            del sys.modules[name]
        # Overwrite anything that was modified (the easy version...)
        sys.modules.update(snapshot)


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
