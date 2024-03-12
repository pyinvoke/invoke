import sys

from functools import wraps
from pytest import skip
from typing import Callable


if sys.platform == "win32":

    def _skip_if_posix(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper


else:

    def _skip_if_posix(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            skip()
            return fn(*args, **kwargs)

        return wrapper


def skip_if_posix(fn: Callable) -> Callable:
    """
    Skip test if posix.
    """
    return _skip_if_posix(fn)
