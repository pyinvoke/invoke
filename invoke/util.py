import fcntl
import logging
import os
import struct
import sys
import termios


# Allow from-the-start debugging (vs toggled during load of tasks module) via
# shell env var
if os.environ.get('INVOKE_DEBUG'):
    logging.basicConfig(level=logging.DEBUG)

# Add top level logger functions to global namespace. Meh.
log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)


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
