# cython: language_level=3
# cython: profile=False

from typing import Callable, Iterable, Any, TypeVar

import cython

_ForeachArgumentType = TypeVar("_ForeachArgumentType")


@cython.ccall
def foreach(f: Callable[[_ForeachArgumentType], Any], iterator: Iterable[_ForeachArgumentType]):
    for x in iterator:
        f(x)
