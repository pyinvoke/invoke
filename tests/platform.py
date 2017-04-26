# Skip on Windows CI, it may blow up on one of these
from invoke.platform import WINDOWS
if not WINDOWS:

    import fcntl
    import termios

    from mock import Mock, patch
    from spec import Spec, eq_, skip

    from invoke.platform import pty_size, bytes_to_read


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
            def defaults_to_80x24_when_stdout_not_a_tty(self, ioctl, stdout):
                # Make sure stdout acts like a real stream (means failure is
                # more obvious)
                stdout.fileno.return_value = 1
                # Ensure it fails the isatty() test too
                stdout.isatty.return_value = False
                # Test
                eq_(pty_size(), (80, 24))

            @patch('sys.stdout')
            @patch('fcntl.ioctl')
            def uses_default_when_stdout_lacks_fileno(self, ioctl, stdout):
                # i.e. when accessing it throws AttributeError
                stdout.fileno.side_effect = AttributeError
                eq_(pty_size(), (80, 24))

            @patch('sys.stdout')
            @patch('fcntl.ioctl')
            def uses_default_when_stdout_triggers_ioctl_error(
                self, ioctl, stdout
            ):
                ioctl.side_effect = TypeError
                eq_(pty_size(), (80, 24))

        class bytes_to_read_:
            @patch('invoke.platform.fcntl')
            def returns_1_when_stream_lacks_fileno(self, fcntl):
                # A fileno() that exists but returns a non-int is a quick way
                # to fail util.has_fileno().
                eq_(bytes_to_read(Mock(fileno=lambda: None)), 1)
                assert not fcntl.ioctl.called

            @patch('invoke.platform.fcntl')
            def returns_1_when_stream_has_fileno_but_is_not_a_tty(self, fcntl):
                # It blows up otherwise anyways (struct.unpack gets mad because
                # result isn't a string of the right length) but let's make
                # ioctl die similarly to the real world case we're testing for
                # here (#425)
                fcntl.ioctl.side_effect = IOError(
                    "Operation not supported by device"
                )
                stream = Mock(
                    isatty=lambda: False,
                    fileno=lambda: 17, # arbitrary
                )
                eq_(bytes_to_read(stream), 1)
                assert not fcntl.ioctl.called

            def returns_FIONREAD_result_when_stream_is_a_tty(self):
                skip()

            def returns_1_on_windows(self):
                skip()
