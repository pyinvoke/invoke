from ._version import __version_info__, __version__  # noqa
from .tasks import task, ctask, Task  # noqa
from .collection import Collection  # noqa
from .context import Context  # noqa
from .config import Config # noqa
from .runners import Runner, Local, Failure # noqa


def run(command, **kwargs):
    """
    Invoke ``command`` in a subprocess and return a `.Result` object.

    This function is simply a convenience wrapper for creating an anonymous
    `.Context` object and calling its `.Context.run` method, which lets you use
    Invoke's powerful local command execution without requiring the rest of its
    API.
    """
    return Context().run(command, **kwargs)
