__all__ = (
    "AmbiguousEnvVar",
    "Argument",
    "AuthFailure",
    "Call",
    "Collection",
    "CollectionNotFound",
    "CommandTimedOut",
    "Config",
    "Context",
    "Executor",
    "Exit",
    "FailingResponder",
    "Failure",
    "FilesystemLoader",
    "Local",
    "MockContext",
    "ParseError",
    "ParseResult",
    "Parser",
    "ParserContext",
    "PlatformError",
    "Program",
    "Promise",
    "Responder",
    "ResponseNotAccepted",
    "Result",
    "Runner",
    "StreamWatcher",
    "SubprocessPipeError",
    "Task",
    "ThreadException",
    "UncastableEnvVar",
    "UnexpectedExit",
    "UnknownFileType",
    "UnpicklableConfigMember",
    "WatcherError",
    "__version__",
    "__version_info__",
    "call",
    "pty_size",
    "task",
)


from importlib import metadata
from typing import Any, Optional

from .collection import Collection
from .config import Config
from .context import Context, MockContext
from .exceptions import (
    AmbiguousEnvVar,
    AuthFailure,
    CollectionNotFound,
    CommandTimedOut,
    Exit,
    ParseError,
    PlatformError,
    ResponseNotAccepted,
    SubprocessPipeError,
    ThreadException,
    UncastableEnvVar,
    UnexpectedExit,
    UnknownFileType,
    UnpicklableConfigMember,
    WatcherError,
)
from .executor import Executor
from .loader import FilesystemLoader
from .parser import Argument, Parser, ParserContext, ParseResult
from .program import Program
from .runners import Failure, Local, Promise, Result, Runner
from .tasks import Call, Task, call, task
from .terminals import pty_size
from .watchers import FailingResponder, Responder, StreamWatcher

__version__ = metadata.version("invoke")


def run(command: str, **kwargs: Any) -> Optional[Result]:
    """
    Run ``command`` in a subprocess and return a `.Result` object.

    See `.Runner.run` for API details.

    .. note::
        This function is a convenience wrapper around Invoke's `.Context` and
        `.Runner` APIs.

        Specifically, it creates an anonymous `.Context` instance and calls its
        `~.Context.run` method, which in turn defaults to using a `.Local`
        runner subclass for command execution.

    .. versionadded:: 1.0
    """
    return Context().run(command, **kwargs)


def sudo(command: str, **kwargs: Any) -> Optional[Result]:
    """
    Run ``command`` in a ``sudo`` subprocess and return a `.Result` object.

    See `.Context.sudo` for API details, such as the ``password`` kwarg.

    .. note::
        This function is a convenience wrapper around Invoke's `.Context` and
        `.Runner` APIs.

        Specifically, it creates an anonymous `.Context` instance and calls its
        `~.Context.sudo` method, which in turn defaults to using a `.Local`
        runner subclass for command execution (plus sudo-related bits &
        pieces).

    .. versionadded:: 1.4
    """
    return Context().sudo(command, **kwargs)
