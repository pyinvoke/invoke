from ._version import __version_info__, __version__  # noqa
from .collection import Collection  # noqa
from .config import Config # noqa
from .context import Context, MockContext  # noqa
from .exceptions import ( # noqa
    AmbiguousEnvVar, ThreadException, ParseError, CollectionNotFound, # noqa
    UnknownFileType, Exit, UncastableEnvVar, PlatformError, # noqa
    ResponseNotAccepted, UnexpectedExit, AuthFailure, WatcherError, # noqa
) # noqa
from .executor import Executor # noqa
from .loader import FilesystemLoader # noqa
from .parser import Argument # noqa
from .platform import pty_size # noqa
from .program import Program # noqa
from .runners import ( # noqa
    Runner, Local, Failure, Result, # noqa
) # noqa
from .tasks import task, call, Call, Task # noqa
from .watchers import ( # noqa
    StreamWatcher, Responder, FailingResponder, # noqa
) # noqa


def run(command, **kwargs):
    """
    Invoke ``command`` in a local subprocess and return a `.Result` object.

    See `.Runner.run` for API details.

    .. note::
        This function is a convenience wrapper around Invoke's `.Context` and
        `.Runner` APIs.

        Specifically, it creates an anonymous `.Context` instance and calls its
        `~.Context.run` method, which in turn defaults to using a `.Local`
        runner subclass for command execution.
    """
    return Context().run(command, **kwargs)
