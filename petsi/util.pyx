#cython: language_level=3

from typing import Callable, Iterator, Any 

def foreach(f: Callable[[Any], Any], iterator: Iterator[Any]):
    for x in iterator:
      f(x)

print("util.pyx")
