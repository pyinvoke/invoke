from typing import Any, Sequence, Union, cast

from invoke.context import Context
from invoke.tasks import Call, Task, task


def body(context: Context) -> None:
    pass


dependency: Task[Any] = Task(body)
configured: Task[Any] = Task(
    body,
    pre=(dependency, Call(dependency)),
    post=[dependency, Call(dependency)],
)
pre: Sequence[Union[Task[Any], Call]] = configured.pre
post: Sequence[Union[Task[Any], Call]] = configured.post
assert configured.pre == (dependency, Call(dependency))


@task(dependency)
def decorated(context: Context) -> None:
    pass


assert cast(Task[Any], decorated).pre == (dependency,)

# Incorrect dependency types must still fail instead of being widened to Any.
invalid: Task[Any] = Task(body, pre=[123])  # type: ignore[list-item]
