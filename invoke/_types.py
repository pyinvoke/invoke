from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Callable,
    Union,
    Sequence,
    overload,
    cast,
    Optional,
    Dict,
)
from typing_extensions import Protocol, TypedDict, Unpack, Literal


if TYPE_CHECKING:
    from invoke.runners import Promise, Result
    from invoke.watchers import StreamWatcher


def annotate_run_function(func: Callable[..., Any]) -> "RunFunction":
    """Add standard run function annotations to a function."""
    return cast(RunFunction, func)


class _BaseRunParams(TypedDict, total=False):
    dry: bool
    echo: bool
    echo_format: str
    echo_stdin: Optional[bool]
    encoding: Optional[str]
    err_stream: IO
    env: Dict[str, str]
    fallback: bool
    hide: Optional[bool]
    in_stream: Optional[IO]
    out_stream: IO
    pty: bool
    replace_env: bool
    shell: str
    timeout: Optional[int]
    warn: bool
    watchers: Sequence["StreamWatcher"]


class RunParams(_BaseRunParams, total=False):
    """Parameters for Runner.run"""

    asynchronous: bool
    disown: bool


class RunFunction(Protocol):
    """A function that runs a command."""

    @overload
    def __call__(
        self,
        command: str,
        *,
        disown: Literal[True],
        **kwargs: Unpack[_BaseRunParams],
    ) -> None:
        ...

    @overload
    def __call__(
        self,
        command: str,
        *,
        disown: bool,
        **kwargs: Unpack[_BaseRunParams],
    ) -> Optional["Result"]:
        ...

    @overload
    def __call__(
        self,
        command: str,
        *,
        asynchronous: Literal[True],
        **kwargs: Unpack[_BaseRunParams],
    ) -> "Promise":
        ...

    @overload
    def __call__(
        self,
        command: str,
        *,
        asynchronous: bool,
        **kwargs: Unpack[_BaseRunParams],
    ) -> Union["Promise", "Result"]:
        ...

    @overload
    def __call__(
        self,
        command: str,
        **kwargs: Unpack[_BaseRunParams],
    ) -> "Result":
        ...

    def __call__(
        self,
        command: str,
        **kwargs: Unpack[RunParams],
    ) -> Optional["Result"]:
        ...
