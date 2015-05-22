from ._version import __version_info__, __version__  # noqa
from .collection import Collection  # noqa
from .config import Config # noqa
from .context import Context  # noqa
from .exceptions import ( # noqa
    AmbiguousEnvVar, ThreadException, ParseError, CollectionNotFound, # noqa
    UnknownFileType, Exit, UncastableEnvVar, PlatformError, # noqa
) # noqa
from .platform import pty_size # noqa
from .runners import Runner, Local, Failure # noqa
from .tasks import task, ctask, Task  # noqa


def run(command, **kwargs):
    """
    Invoke ``command`` in a subprocess and return a `.Result` object.

    This function is simply a convenience wrapper for creating an anonymous
    `.Context` object and calling its `.Context.run` method, which lets you use
    Invoke's powerful local command execution without requiring the rest of its
    API.
    """
    return Context().run(command, **kwargs)
