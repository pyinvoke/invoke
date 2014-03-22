"""Cross-platform compatibility wrappers"""

import sys

if sys.platform == 'win32':
    # Windows support (excluding cygwin)

    is_win = True
    pexpect = None

    # Use colorama if the user has it installed, to give ANSI color support
    try:
        import colorama
        colorama.init()
    except ImportError:
        # We will get raw ANSI codes on screen
        pass

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

    def pty_size():
        """
        Return terminal size as ``(num_cols, num_rows)`` tuple.

        If unable to determine, defaults to 80x24.
        """
        GetStdHandle = windll.kernel32.GetStdHandle
        GetConsoleScreenBufferInfo = windll.kernel32.GetConsoleScreenBufferInfo
        GetStdHandle.restype = HANDLE
        GetConsoleScreenBufferInfo.argtypes = [HANDLE, POINTER(CONSOLE_SCREEN_BUFFER_INFO)]

        hstd = GetStdHandle(-11) # STD_OUTPUT_HANDLE = -11
        csbi = CONSOLE_SCREEN_BUFFER_INFO()
        ret = GetConsoleScreenBufferInfo(hstd, byref(csbi))

        if ret:
            sizex = csbi.srWindow.Right - csbi.srWindow.Left + 1
            sizey = csbi.srWindow.Bottom - csbi.srWindow.Top + 1
            return sizex, sizey
        else:
            return (80, 24)

else:
    # POSIX support - includes cygwin

    is_win = False
    from .vendor import pexpect


    import fcntl
    import struct
    import termios

    def pty_size():
        """
        Return local (stdout-based) pty size as ``(num_cols, num_rows)`` tuple.

        If unable to determine (e.g. ``sys.stdout`` has been monkeypatched, or
        ``termios`` lacking ``TIOCGWINSZ``) defaults to 80x24.
        """
        default_cols, default_rows = 80, 24
        cols, rows = default_cols, default_rows
        if sys.stdout.isatty():
            # We want two short unsigned integers (rows, cols)
            fmt = 'HH'
            # Create an empty (zeroed) buffer for ioctl to map onto. Yay for C!
            buffer = struct.pack(fmt, 0, 0)
            # Call TIOCGWINSZ to get window size of stdout, returns our filled
            # buffer
            try:
                result = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ,
                    buffer)
                # Unpack buffer back into Python data types
                # NOTE: this unpack gives us rows x cols, but we return the
                # inverse.
                rows, cols = struct.unpack(fmt, result)
                # Fall back to defaults if TIOCGWINSZ returns unreasonable values
                if rows == 0:
                    rows = default_rows
                if cols == 0:
                    cols = default_cols
            # Deal with e.g. sys.stdout being monkeypatched, such as in testing.
            # Or termios not having a TIOCGWINSZ.
            except AttributeError:
                pass
        return cols, rows
