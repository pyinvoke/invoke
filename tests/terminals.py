import fcntl
import struct
import termios

from unittest.mock import Mock, patch
from pytest import skip, mark

from invoke.terminals import pty_size, bytes_to_read, WINDOWS

# Skip on Windows CI, it may blow up on one of these tests
pytestmark = mark.skipif(
    WINDOWS, reason="Low level terminal tests only work well on POSIX"
)


# NOTE: 'with character_buffered()' tests are in runners.py as it's a lot
# easier to test some aspects in a non-unit sense (e.g. a keyboard-interrupting
# Runner subclass). MEH.


class terminals:
    class pty_size:
        @patch("fcntl.ioctl", wraps=fcntl.ioctl)
        def calls_fcntl_with_TIOCGWINSZ(self, ioctl):
            # Test the default (Unix) implementation because that's all we
            # can realistically do here.
            pty_size()
            assert ioctl.call_args_list[0][0][1] == termios.TIOCGWINSZ

        @patch("sys.stdout")
        @patch("fcntl.ioctl")
        def defaults_to_80x24_when_stdout_not_a_tty(self, ioctl, stdout):
            # Make sure stdout acts like a real stream (means failure is
            # more obvious)
            stdout.fileno.return_value = 1
            # Ensure it fails the isatty() test too
            stdout.isatty.return_value = False
            # Test
            assert pty_size() == (80, 24)

        @patch("sys.stdout")
        @patch("fcntl.ioctl")
        def uses_default_when_stdout_lacks_fileno(self, ioctl, stdout):
            # i.e. when accessing it throws AttributeError
            stdout.fileno.side_effect = AttributeError
            assert pty_size() == (80, 24)

        @patch("sys.stdout")
        @patch("fcntl.ioctl")
        def uses_default_when_stdout_triggers_ioctl_error(self, ioctl, stdout):
            ioctl.side_effect = TypeError
            assert pty_size() == (80, 24)

    class bytes_to_read_:
        @patch("invoke.terminals.fcntl")
        def returns_1_when_stream_lacks_fileno(self, fcntl):
            # A fileno() that exists but returns a non-int is a quick way
            # to fail util.has_fileno().
            assert bytes_to_read(Mock(fileno=lambda: None)) == 1
            assert not fcntl.ioctl.called

        @patch("invoke.terminals.fcntl")
        def returns_1_when_stream_has_fileno_but_is_not_a_tty(self, fcntl):
            # It blows up otherwise anyways (struct.unpack gets mad because
            # result isn't a string of the right length) but let's make
            # ioctl die similarly to the real world case we're testing for
            # here (#425)
            fcntl.ioctl.side_effect = IOError(
                "Operation not supported by device"
            )
            stream = Mock(isatty=lambda: False, fileno=lambda: 17)  # arbitrary
            assert bytes_to_read(stream) == 1
            assert not fcntl.ioctl.called

        @patch("invoke.terminals.fcntl")
        def uses_4_byte_buffer_for_FIONREAD(self, fcntl):
            # FIONREAD writes a C int (4 bytes); the buffer must match to
            # avoid SystemError on Python 3.14+ (#1070)
            fcntl.ioctl.return_value = struct.pack("i", 42)
            stream = Mock(isatty=lambda: True, fileno=lambda: 7)
            assert bytes_to_read(stream) == 42
            buf = fcntl.ioctl.call_args[0][2]
            assert len(buf) == 4

        @patch("invoke.terminals.fcntl")
        def returns_0_when_FIONREAD_is_zero(self, fcntl):
            fcntl.ioctl.return_value = struct.pack("i", 0)
            stream = Mock(isatty=lambda: True, fileno=lambda: 7)
            assert bytes_to_read(stream) == 0

        def returns_FIONREAD_result_when_stream_is_a_tty(self):
            skip()

        def returns_1_on_windows(self):
            skip()
