# TODO: skip on Windows CI, it may blow up on one of these
import fcntl
import termios

from mock import patch
from spec import Spec, eq_

from invoke.platform import pty_size


class platform(Spec):
    class pty_size:
        @patch('fcntl.ioctl', wraps=fcntl.ioctl)
        def calls_fcntl_with_TIOCGWINSZ(self, ioctl):
            # Test the default (Unix) implementation because that's all we
            # can realistically do here.
            pty_size()
            eq_(ioctl.call_args_list[0][0][1], termios.TIOCGWINSZ)

        @patch('sys.stdout')
        @patch('fcntl.ioctl')
        def uses_default_when_stdout_lacks_fileno(self, ioctl, stdout):
            # i.e. when accessing it throws AttributeError
            stdout.fileno.side_effect = AttributeError
            eq_(pty_size(), (80, 24))
            # Make sure we skipped over ioctl
            assert not ioctl.called

        @patch('sys.stdout')
        @patch('fcntl.ioctl')
        def defaults_to_80x24_when_stdout_not_a_tty(self, ioctl, stdout):
            # Make sure stdout acts like a real stream (means failure is
            # more obvious)
            stdout.fileno.return_value = 1
            # Ensure it fails the isatty() test
            stdout.isatty.return_value = False
            # Test
            eq_(pty_size(), (80, 24))
            # Make sure we skipped over ioctl
            assert not ioctl.called
