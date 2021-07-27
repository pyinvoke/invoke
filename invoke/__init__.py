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
from inoke.executor import Executor  # noqa
from inoke.loader import FilesystemLoader  # noqa
from inoke.parser import Argument, Parser, ParserContext, ParseResult  # noqa
from inoke.program import Program  # noqa
from inoke.runners import Runner, Local, Failure, Result, Promise  # noqa
from inoke.tasks import task, call, Call, Task  # noqa
from inoke.terminals import pty_size  # noqa
from inoke.watchers import FailingResponder, Responder, StreamWatcher  # noqa


def run(command, **kwargs):
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


def sudo(command, **kwargs):
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
