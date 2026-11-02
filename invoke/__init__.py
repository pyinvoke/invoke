from importlib import metadata
from typing import Any

from .collection import Collection as Collection  # noqa
from .config import Config as Config  # noqa
from .context import Context as Context, MockContext as MockContext  # noqa
from .exceptions import (  # noqa
    AmbiguousEnvVar as AmbiguousEnvVar,
    AuthFailure as AuthFailure,
    CollectionNotFound as CollectionNotFound,
    CommandTimedOut as CommandTimedOut,
    Exit as Exit,
    ParseError as ParseError,
    PlatformError as PlatformError,
    ResponseNotAccepted as ResponseNotAccepted,
    SubprocessPipeError as SubprocessPipeError,
    ThreadException as ThreadException,
    UncastableEnvVar as UncastableEnvVar,
    UnexpectedExit as UnexpectedExit,
    UnknownFileType as UnknownFileType,
    UnpicklableConfigMember as UnpicklableConfigMember,
    WatcherError as WatcherError,
)
from .executor import Executor as Executor  # noqa
from .loader import FilesystemLoader as FilesystemLoader  # noqa
from .parser import (
    Argument as Argument,
    Parser as Parser,
    ParserContext as ParserContext,
    ParseResult as ParseResult,
)  # noqa
from .program import Program as Program  # noqa
from .runners import (
    Failure as Failure,
    Local as Local,
    Promise as Promise,
    Result as Result,
    Runner as Runner,
)  # noqa
from .tasks import (
    Call as Call,
    Task as Task,
    call as call,
    task as task,
)  # noqa
from .terminals import pty_size as pty_size  # noqa
from .watchers import (
    FailingResponder as FailingResponder,
    Responder as Responder,
    StreamWatcher as StreamWatcher,
)  # noqa

__all__ = [
    "Collection",
    "Config",
    "Context",
    "MockContext",
    "AmbiguousEnvVar",
    "AuthFailure",
    "CollectionNotFound",
    "CommandTimedOut",
    "Exit",
    "ParseError",
    "PlatformError",
    "ResponseNotAccepted",
    "SubprocessPipeError",
    "ThreadException",
    "UncastableEnvVar",
    "UnexpectedExit",
    "UnknownFileType",
    "UnpicklableConfigMember",
    "WatcherError",
    "Executor",
    "FilesystemLoader",
    "Argument",
    "Parser",
    "ParserContext",
    "ParseResult",
    "Program",
    "Failure",
    "Local",
    "Promise",
    "Result",
    "Runner",
    "Call",
    "Task",
    "call",
    "task",
    "pty_size",
    "FailingResponder",
    "Responder",
    "StreamWatcher",
    "run",
    "sudo",
    "__version__",
]

__version__ = metadata.version("invoke")


def run(command: str, **kwargs: Any) -> Result:
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


def sudo(command: str, **kwargs: Any) -> Result:
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
