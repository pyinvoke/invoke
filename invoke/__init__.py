from typing import Any, Optional

from ._version import __version_info__, __version__  # noqa
from .collection import Collection  # noqa
from .config import Config  # noqa
from .context import Context, MockContext  # noqa
from .exceptions import (  # noqa
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
from .executor import Executor  # noqa
from .loader import FilesystemLoader  # noqa
from .parser import Argument, Parser, ParserContext, ParseResult  # noqa
from .program import Program  # noqa
from .runners import Failure, Local, Promise, Result, Runner  # noqa
from .tasks import Call, Task, call, task  # noqa
from .terminals import pty_size  # noqa
from .watchers import FailingResponder, Responder, StreamWatcher  # noqa


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
