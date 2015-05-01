import os
import sys
from functools import partial

from spec import eq_, skip, Spec, raises, ok_, trap
from mock import patch, Mock

from invoke import run
from invoke.config import Config
from invoke.context import Context
from invoke.runners import Runner, Local
from invoke.exceptions import Failure
from invoke.platform import WINDOWS

from _utils import support, reset_cwd, skip_if_windows


# TODO: split this stuff up between runners.py (more correctly organized, &
# mocked lower level) and integration/ (not mocked at all).
# TODO: many tests may want to be copied into both places.

# Get the right platform-specific directory separator,
# because Windows command parsing doesn't like '/'
error_command = "{0} err.py".format(sys.executable)

def _run(returns=None, **kwargs):
    """
    Create a Runner w/ retval reflecting ``returns`` & call ``run(**kwargs)``.
    """
    # Set up return value tuple for Runner.run_direct
    returns = returns or {}
    returns.setdefault('exited', 0)
    value = map(
        lambda x: returns.get(x, None),
        ('stdout', 'stderr', 'exited', 'exception'),
    )
    class MockRunner(Runner):
        def run_direct(self, command, **kwargs):
            return value
    return MockRunner(Context()).run("whatever", **kwargs)


def _runner(key, config_val):
    # Config reflecting given data
    c = Context(config=Config(overrides={'run': {key: config_val}}))
    # Runner w/ methods mocked for inspection (& to prevent actual subprocess)
    r = Runner(context=c)
    r.run_direct = Mock(return_value=("", "", 0, None))
    r.run_direct.__name__ = 'run_direct'
    return r

def _config_check(key, config_val, kwarg_val, expected, func='run_direct'):
    r = _runner(key=key, config_val=config_val)
    # NOTE: mocking select_method this way means result pty info is incorrect.
    # Doesn't matter for these tests.
    r.select_method = Mock(return_value=r.run_direct)
    kwargs = {}
    if kwarg_val is not None:
        kwargs[key] = kwarg_val
    r.run('whatever', **{key: kwarg_val})
    eq_(getattr(r, func).call_args[1][key], expected)


# Shorthand for mocking Local.run_pty so tests run under non-pty environments
# don't asplode.
_patch_run_pty = patch.object(
    Local,
    'run_pty',
    return_value=('', '', 0, None),
    func_name='run_pty',
    __name__='run_pty',
)

# Shorthand for mocking os.isatty
_is_tty = patch('os.isatty', return_value=True)
_not_tty = patch('os.isatty', return_value=False)


class Run(Spec):
    "Basic run() / Context.run() behavior"

    def setup(self):
        os.chdir(support)
        self.both = "echo foo && {0} bar".format(error_command)
        self.out = "echo foo"
        self.err = "{0} bar".format(error_command)
        self.sub = "inv -c pty_output hide_{0}"

    def teardown(self):
        reset_cwd()

