""" Useful code fragments that do not fit in any other particular module."""

import sys


def export(fn):
    """ A decorator for annotating top level public objects in a module.

    It makes the decorated object be part of the module's public API by adding it
    to the ``__all__`` variable of the defining module.

    Taken from Aaron Hall's
    `Stackoverflow answer <https://stackoverflow.com/questions/44834/can-someone-explain-all-in-python>`_
    """
    mod = sys.modules[fn.__module__]
    if hasattr(mod, '__all__'):
        mod.__all__.append(fn.__name__)
    else:
        mod.__all__ = [fn.__name__]
    return fn
