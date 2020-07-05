""" A sub-package defining the interface for PetSi plugins and implementing a number of built-in plugins.

**Synopsis:**

.. code-block:: python

    from .plugins import AutoFirePlugin
    plugin = AutoFirePlugin(...)

    from .plugins import SojournTimePlugin
    plugin = SojournTimePlugin(...)

    from .plugins import TokenCounterPlugin
    plugin = TokenCounterPlugin(...)

    from .plugins import TransitionIntervalPlugin
    plugin = TransitionIntervalPlugin(...)

.. autodata:: AutoFirePlugin
    :noindex:

    For the interface documentation, refer to :class:`.autofire.AutoFirePlugin`.

.. autodata:: SojournTimePlugin
    :noindex:

    For the interface documentation, refer to :class:`~.sojourntime.SojournTimePlugin`.

.. autodata:: TokenCounterPlugin
    :noindex:

    For the interface documentation, refer to :class:`~.tokencounter.TokenCounterPlugin`.

.. autodata:: TransitionIntervalPlugin
    :noindex:

    For the interface documentation, refer to :class:`~.transitioninterval.TransitionIntervalPlugin`.

.. rubric:: Internal submodules

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
