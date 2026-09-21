from typing import Callable, Optional

from invoke import Context, Task


def number(context: Context) -> int:
    return 3


def text(context: Context) -> str:
    return "value"


def nothing(context: Context) -> None:
    pass


def optional(context: Context) -> Optional[int]:
    return None


number_task: Task[Callable[[Context], int]] = Task(number)
text_task: Task[Callable[[Context], str]] = Task(text)
nothing_task: Task[Callable[[Context], None]] = Task(nothing)
optional_task: Task[Callable[[Context], Optional[int]]] = Task(optional)

number_result: int = number_task(Context())
text_result: str = text_task(Context())
nothing_result: None = nothing_task(Context())
optional_result: Optional[int] = optional_task(Context())

# These must remain errors: returning Any would hide incorrect result usage.
wrong_number: str = number_task(Context())  # type: ignore[assignment]
wrong_text: int = text_task(Context())  # type: ignore[assignment]
wrong_optional: int = optional_task(Context())  # type: ignore[assignment]


class Body:
    def __call__(self, context: Context) -> str:
        return "callable object"


def callback(context: Context) -> Callable[[], int]:
    return lambda: 7


object_task: Task[Body] = Task(Body())
callback_task: Task[Callable[[Context], Callable[[], int]]] = Task(callback)
object_result: str = object_task(Context())
callback_result: Callable[[], int] = callback_task(Context())
wrong_object: int = object_task(Context())  # type: ignore[assignment]
wrong_callback: int = callback_task(Context())  # type: ignore[assignment]
