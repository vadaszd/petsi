""" A sub-package defining the interface for PetSi plugins and implementing a number of built-in plugins.

.. rubric:: Package interface

.. autosummary
    :template: package_interface_class.rst
    :recursive:
    :toctree:

.. autodata:: AutoFirePlugin
    :noindex:

.. autodata:: SojournTimePlugin
    :noindex:

.. autodata:: TokenCounterPlugin
    :noindex:

.. autodata:: TransitionIntervalPlugin
    :noindex:


.. rubric:: Private modules

.. autosummary::
    :template: module_reference.rst
    :recursive:
    :toctree:

    petsi.plugins._meters
"""

from .autofire import AutoFirePlugin
from .sojourntime import SojournTimePlugin
from .tokencounter import TokenCounterPlugin
from .transitioninterval import TransitionIntervalPlugin
