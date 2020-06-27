from typing import Callable, Iterable, Any, TypeVar

_ForeachArgumentType = TypeVar("_ForeachArgumentType")

def foreach(f: Callable[[_ForeachArgumentType], Any], iterable: Iterable[_ForeachArgumentType]):
    """ Call f on each element of the iterable.
    :param f: A function accepting a single argument of the type of the elements of the iterable
    :param iterable: An iterable providing elements accepted by the function
    :return: None
    """