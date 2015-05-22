"""
Custom exception classes.

These vary in use case from "we needed a specific data structure layout in
exceptions used for message-passing" to simply "we needed to express an error
condition in a way easily told apart from other, truly unexpected errors".
"""

from collections import namedtuple
from traceback import format_exception
from pprint import pformat

from .vendor import six


class CollectionNotFound(Exception):
    def __init__(self, name, start):
        self.name = name
        self.start = start


class Failure(Exception):
    """
    Exception subclass representing failure of a command execution.

    It exhibits a ``result`` attribute containing the related `.Result` object,
    whose attributes may be inspected to determine why the command failed.
    """
    def __init__(self, result):
        self.result = result

    def __str__(self):
        err_label = "Stderr"
        err_text = self.result.stderr
        if self.result.pty:
            err_label = "Stdout (pty=True; no stderr possible)"
            err_text = self.result.stdout
        return """Command execution failure!

Exit code: {0}

{1}:

{2}

""".format(self.result.exited, err_label, err_text)

    def __repr__(self):
        return str(self)


class ParseError(Exception):
    def __init__(self, msg, context=None):
        super(ParseError, self).__init__(msg)
        self.context = context


class Exit(Exception):
    """
    Simple stand-in for SystemExit that lets us gracefully exit.

    Removes lots of scattered sys.exit calls, improves testability.
    """
    def __init__(self, code=0):
        self.code = code


class PlatformError(Exception):
    """
    Raised when an illegal operation occurs for the current platform.

    E.g. Windows users trying to use functionality requiring the ``pty``
    module.

    Typically used to present a clearer error message to the user.
    """
    pass


class AmbiguousEnvVar(Exception):
    """
    Raised when loading env var config keys has an ambiguous target.
    """
    pass


class UncastableEnvVar(Exception):
    """
    Raised on attempted env var loads whose default values are too rich.

    E.g. trying to stuff ``MY_VAR="foo"`` into ``{'my_var': ['uh', 'oh']}``
    doesn't make any sense until/if we implement some sort of transform option.
    """
    pass


class UnknownFileType(Exception):
    """
    A config file of an unknown type was specified and cannot be loaded.
    """
    pass


#: A namedtuple wrapping a thread-borne exception & that thread's arguments.
ExceptionWrapper = namedtuple(
    'ExceptionWrapper',
    'kwargs type value traceback'
)

def _printable_kwargs(kwargs):
    """
    Return print-friendly version of a thread-related ``kwargs`` dict.

    Extra care is taken with ``args`` members which are very long iterables -
    those need truncating to be useful.
    """
    printable = {}
    for key, value in six.iteritems(kwargs):
        item = value
        if key == 'args':
            item = []
            for arg in value:
                new_arg = arg
                if hasattr(arg, '__len__') and len(arg) > 10:
                    msg = "<... remainder truncated during error display ...>"
                    new_arg = arg[:10] + [msg]
                item.append(new_arg)
        printable[key] = item
    return printable

class ThreadException(Exception):
    """
    One or more exceptions were raised within background (usually I/O) threads.

    The real underlying exceptions are stored in the `exceptions` attribute;
    see its documentation for data structure details.

    .. note::
        Threads which did not encounter an exception, do not contribute to this
        exception object and thus are not present inside `exceptions`.
    """
    #: A tuple of `ExceptionWrappers <ExceptionWrapper>` containing the initial
    #: thread constructor kwargs (because `threading.Thread` subclasses should
    #: always be called with kwargs) and the caught exception for that thread
    #: as seen by `sys.exc_info` (so: type, value, traceback).
    #:
    #: .. note::
    #:     The ordering of this attribute is not well-defined.
    #:
    #: .. note::
    #:     Thread kwargs which appear to be very long (e.g. IO
    #:     buffers) will be truncated when printed, to avoid huge
    #:     unreadable error display.
    exceptions = tuple()

    def __init__(self, exceptions):
        self.exceptions = tuple(exceptions)

    def __str__(self):
        details = []
        for x in self.exceptions:
            # Build useful display
            detail = "Thread args: {0}\n\n{1}"
            details.append(detail.format(
                pformat(_printable_kwargs(x.kwargs)),
                "\n".join(format_exception(x.type, x.value, x.traceback)),
            ))
        args = (
            len(self.exceptions),
            ", ".join(x.type.__name__ for x in self.exceptions),
            "\n\n".join(details),
        )
        return """
Saw {0} exceptions within threads ({1}):


{2}
""".format(*args)
