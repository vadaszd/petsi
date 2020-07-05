""" A plugin that fires enabled transitions automatically.

.. rubric:: Synopsis

.. code-block:: python

    from .autofire import AutoFirePlugin

    if TYPE_CHECKING:
        from .autofire import Clock

   plugin = AutoFirePlugin(...)

- Refer to :class:`AutoFirePlugin` below.
- .. autodata:: Clock
    :noindex:

    ``Clock`` is exported here only for type-checking purposes. It should not be instantiated.

.. rubric:: Internal submodules

.. autosummary::
    :template: module_reference.rst
    :recursive:
    :toctree:

    petsi.plugins.autofire._autofire
"""

from dataclasses import dataclass, field
from functools import cached_property
from itertools import repeat
from typing import Callable, Optional, TYPE_CHECKING

from ...util import export

from ..._structure import foreach
from ..Plugins import AbstractPlugin
from ._autofire import FireControl, AutoFirePluginTransitionObserver, Clock

if TYPE_CHECKING:
    from ..Plugins import NoopPlaceObserver, NoopTokenObserver
    from ..._structure import Transition

export(Clock)


@export
@dataclass(eq=False)
class AutoFirePlugin(
        AbstractPlugin["NoopPlaceObserver", "AutoFirePluginTransitionObserver", "NoopTokenObserver"]):
    """ A PetSi plugin for firing transitions automatically.

    The actual work of selecting and firing the transitions is delegated to the
    :mod:`~._autofire` Cython extension module.

    The transitions are selected for firing based on the rules for
    Extended Stochastic Petri Nets. For the details, see the documentation of :mod:`~._autofire`.
    """

    _fire_control: FireControl = field(default_factory=FireControl, init=False)

    @cached_property
    def clock(self) -> Clock:
        """ A :class:`petsi._autofire.Clock` instance tracking the progress of Petri net time"""
        return self._fire_control.get_clock()

    def reset(self):
        self._fire_control.reset()

    def fire_while(self, condition: Callable[[], bool]):
        """ Keep randomly firing transitions while ``condition`` is met or the enabled transitions are exhausted."""
        self._fire_control.start()

        while condition():
            self._fire_control.fire_next()

    def fire_until(self, end_time: float):
        """ Keep randomly firing transitions until the Petri net time reaches or exceeds ``end_time``.

            Firing will stop earlier if there are no more enabled transitions.
        """
        read_clock = self.clock.read
        self.fire_while(lambda: read_clock() < end_time)

    def fire_repeatedly(self, count_of_firings: int = 0):
        """ Perform ``count_of_firings`` firings on randomly selected transitions.

            Firing will stop earlier if there are no more enabled transitions.
        """
        self._fire_control.start()

        foreach(lambda _: self._fire_control.fire_next(),
                repeat(None) if count_of_firings == 0 else repeat(None, count_of_firings))

    def transition_observer_factory(self, t: "Transition") -> Optional[AutoFirePluginTransitionObserver]:
        """ Creates and returns a :class:`petsi._autofire.AutoFirePluginTransitionObserver` """
        return AutoFirePluginTransitionObserver(self, t, self._fire_control)
