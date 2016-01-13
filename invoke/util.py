from contextlib import contextmanager
import logging
import os


LOG_FORMAT = "%(name)s.%(module)s.%(funcName)s: %(message)s"

def enable_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
    )

# Allow from-the-start debugging (vs toggled during load of tasks module) via
# shell env var.
if os.environ.get('INVOKE_DEBUG'):
    enable_logging()

# Add top level logger functions to global namespace. Meh.
log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)


def sort_names(names):
    """
    Sort task ``names`` by nesting depth & then as regular strings.
    """
    return sorted(names, key=lambda x: (x.count('.'), x))


# TODO: Make part of public API sometime
@contextmanager
def cd(where):
    cwd = os.getcwd()
    os.chdir(where)
    try:
        yield
    finally:
        os.chdir(cwd)


def isatty(stream):
    """
    Attempt to rigorously determine whether ``stream`` is input from a TTY.

    Used in a few spots where we care whether stdin is a real live terminal or
    something else (for example, a ``StringIO``, or any other mocked/replaced
    stream - some of which may not correctly implement the ``isatty`` method!)

    :param stream: The stream object in question; it's usually `sys.stdin`.

    :returns:
        ``True`` if ``stream`` does seem to be a TTY, ``False`` otherwise.
    """
    # If there *is* an .isatty, ask it.
    if hasattr(stream, 'isatty') and callable(stream.isatty):
        return stream.isatty()
    # If there wasn't, see if it has a fileno, and if so, ask os.isatty
    if hasattr(stream, 'fileno') and callable(stream.fileno):
        # NOTE: the default impl of io classes actually has an exploding
        # .fileno(), but the same impl has a useful .isatty(), so...
        return os.isatty(stream.fileno())
    # If we got here, none of the above worked, so it's reasonable to assume
    # the darn thing isn't a real TTY.
    return False
