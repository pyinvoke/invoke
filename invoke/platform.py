"""
Platform-specific code lives here.

This is its own module to abstract away what would otherwise be distracting logic-flow interruptions.
"""

import sys
WINDOWS = (sys.platform == 'win32')
"""
Whether or not the current platform appears to be Windows in nature.

Note that Cygwin's Python is actually close enough to "real" UNIXes that it
doesn't need (or want!) to use PyWin32 -- so we only test for literal Win32
setups (vanilla Python, ActiveState etc) here.
"""


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
    import fcntl
    import struct
    import termios

    # Sentinel values to be replaced w/ defaults by caller
    size = (None, None)
    # Can only get useful values from real TTYs
    if sys.stdout.isatty():
        # We want two short unsigned integers (rows, cols)
        fmt = 'HH'
        # Create an empty (zeroed) buffer for ioctl to map onto. Yay for C!
        buf = struct.pack(fmt, 0, 0)
        # Call TIOCGWINSZ to get window size of stdout, returns our filled
        # buffer
        try:
            result = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, buf)
            # Unpack buffer back into Python data types
            # NOTE: this unpack gives us rows x cols, but we return the
            # inverse.
            rows, cols = struct.unpack(fmt, result)
            return (cols, rows)
        # Deal with e.g. sys.stdout being monkeypatched, such as in testing.
        # Or termios not having a TIOCGWINSZ.
        except AttributeError:
            pass
    return size


def _win_pty_size():
    from ctypes import Structure, c_ushort, windll, POINTER, byref
    from ctypes.wintypes import HANDLE, _COORD, _SMALL_RECT

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
