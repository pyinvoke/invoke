"""
Platform-specific code lives here.

This is its own module to abstract away what would otherwise be distracting
logic-flow interruptions.
"""

from contextlib import contextmanager
import select
import sys

# TODO: move in here? They're currently platform-agnostic...
from .util import has_fileno, isatty


WINDOWS = (sys.platform == 'win32')
"""
Whether or not the current platform appears to be Windows in nature.

Note that Cygwin's Python is actually close enough to "real" UNIXes that it
doesn't need (or want!) to use PyWin32 -- so we only test for literal Win32
setups (vanilla Python, ActiveState etc) here.
"""

if WINDOWS:
    import msvcrt
    from ctypes import Structure, c_ushort, windll, POINTER, byref
    from ctypes.wintypes import HANDLE, _COORD, _SMALL_RECT
    # Dummy definitions for modules imported under Unix, as the tests
    # (that are skipped under Windows anyway) patch them
    fcntl = None
    struct = None
    termios = None
    tty = None
else:
    import fcntl
    import struct
    import termios
    import tty


def pty_size():
    """
    Determine current local pseudoterminal dimensions.

    :returns:
        A ``(num_cols, num_rows)`` two-tuple describing PTY size. Defaults to
        ``(80, 24)`` if unable to get a sensible result dynamically.
    """
    cols, rows = _pty_size() if not WINDOWS else _win_pty_size()
    # TODO: make defaults configurable?
    return ((cols or 80), (rows or 24))


def _pty_size():
    """
    Suitable for most POSIX platforms.
    """
    # Sentinel values to be replaced w/ defaults by caller
    size = (None, None)
    # We want two short unsigned integers (rows, cols)
    fmt = 'HH'
    # Create an empty (zeroed) buffer for ioctl to map onto. Yay for C!
    buf = struct.pack(fmt, 0, 0)
    # Call TIOCGWINSZ to get window size of stdout, returns our filled
    # buffer
    try:
        result = fcntl.ioctl(sys.stdout, termios.TIOCGWINSZ, buf)
        # Unpack buffer back into Python data types
        # NOTE: this unpack gives us rows x cols, but we return the
        # inverse.
        rows, cols = struct.unpack(fmt, result)
        return (cols, rows)
    # Fallback to emptyish return value in various failure cases:
    # * sys.stdout being monkeypatched, such as in testing, and lacking .fileno
    # * sys.stdout having a .fileno but not actually being attached to a TTY
    # * termios not having a TIOCGWINSZ attribute (happens sometimes...)
    # * other situations where ioctl doesn't explode but the result isn't
    #   something unpack can deal with
    except (struct.error, TypeError, IOError, AttributeError):
        pass
    return size


def _win_pty_size():
    class CONSOLE_SCREEN_BUFFER_INFO(Structure):
        _fields_ = [
            ('dwSize', _COORD),
            ('dwCursorPosition', _COORD),
            ('wAttributes', c_ushort),
            ('srWindow', _SMALL_RECT),
            ('dwMaximumWindowSize', _COORD)
        ]

    GetStdHandle = windll.kernel32.GetStdHandle
    GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
    GetStdHandle.restype = HANDLE
    GetConsoleScreenBufferInfo.argtypes = [
        HANDLE, POINTER(CONSOLE_SCREEN_BUFFER_INFO)
    ]

    hstd = GetStdHandle(-11) # STD_OUTPUT_HANDLE = -11
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    ret = GetConsoleScreenBufferInfo(hstd, byref(csbi))

    if ret:
        sizex = csbi.srWindow.Right - csbi.srWindow.Left + 1
        sizey = csbi.srWindow.Bottom - csbi.srWindow.Top + 1
        return sizex, sizey
    else:
        return (None, None)


@contextmanager
def character_buffered(stream):
    """
    Force local terminal ``stream`` be character, not line, buffered.

    Only applies to Unix-based systems; on Windows this is a no-op.
    """
    if WINDOWS or not isatty(stream):
        yield
    else:
        old_settings = termios.tcgetattr(stream)
        tty.setcbreak(stream)
        try:
            yield
        finally:
            termios.tcsetattr(stream, termios.TCSADRAIN, old_settings)


def ready_for_reading(input_):
    """
    Test ``input_`` to determine whether a read action will succeed.

    :param input_: Input stream object (file-like).

    :returns: ``True`` if a read should succeed, ``False`` otherwise.
    """
    # A "real" terminal stdin needs select/kbhit to tell us when it's ready for
    # a nonblocking read().
    # Otherwise, assume a "safer" file-like object that can be read from in a
    # nonblocking fashion (e.g. a StringIO or regular file).
    if not has_fileno(input_):
        return True
    if WINDOWS:
        return msvcrt.kbhit()
    else:
        reads, _, _ = select.select([input_], [], [], 0.0)
        return bool(reads and reads[0] is input_)


def read_byte(input_):
    """
    Read 1 byte from stdin stream ``input_``.

    :param input_: Input stream object (file-like).

    :returns:
        The read byte (a ``str`` or ``bytes`` depending on Python version.)
    """
    # NOTE: there may be dragons here re: what exactly input_ is and what mode
    # it has been opened in.
    # NOTE: changed from
    #       return msvcrt.getch() if WINDOWS else input_.read(1)
    # Using msvcrt.getch is unequivocally wrong - it ignores the argument
    # input_, and its behaviour isn't even what we want if input_ is
    # the console. It returns a byte, which is not what input_.read() does
    # (in spite of the function name!) when input_is opened in text mode
    # like sys.stdin. And when the user presses a special key like F1 (or even
    # just a non-ASCII international character) it returns the first byte of
    # a control sequence that isn't even valid encoded Unicode.
    return input_.read(1)
