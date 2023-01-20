from typing import Any

from invoke._version import __version_info__, __version__  # noqa
from invoke.collection import Collection  # noqa
from invoke.config import Config  # noqa
from invoke.context import Context, MockContext  # noqa
from invoke.exceptions import (  # noqa
    AmbiguousEnvVar,
    AuthFailure,
    CollectionNotFound,
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
    CommandTimedOut,
)
from invoke.executor import Executor  # noqa
from invoke.loader import FilesystemLoader  # noqa
from invoke.parser import Argument, Parser, ParserContext, ParseResult  # noqa
from invoke.program import Program  # noqa
from invoke.runners import Runner, Local, Failure, Result, Promise  # noqa
from invoke.tasks import task, call, Call, Task  # noqa
from invoke.terminals import pty_size  # noqa
from invoke.watchers import FailingResponder, Responder, StreamWatcher  # noqa


def run(command: str, **kwargs: Any) -> Any:
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


def sudo(command: str, **kwargs: Any) -> Any:
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
