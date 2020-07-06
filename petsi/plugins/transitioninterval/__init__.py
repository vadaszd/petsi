""" A plugin package that collects stats on the time intervals between firings of transitions.

Package interface
..................................................

- Class :class:`TransitionIntervalPlugin` (see below)

Internal modules
..................................................

.. autosummary::
    :template: module_reference.rst
    :recursive:
    :toctree:

    petsi.plugins.transitioninterval._transitioninterval
"""
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from ..meters import MeterPlugin
from ...util import export

from ._transitioninterval import FiringCollector, TransitionIntervalPluginTransitionObserver

if TYPE_CHECKING:
    from ..interface import NoopTokenObserver, NoopTransitionObserver
    from ..._structure import Transition


@export
@dataclass(eq=False)
class TransitionIntervalPlugin(
        MeterPlugin[FiringCollector,
                    "NoopPlaceObserver", "TransitionIntervalPluginTransitionObserver", "NoopTokenObserver"]):
    """ A PetSi plugin for collecting stats on the time intervals between firings of transitions."""

    def __post_init__(self):
        self._collector = FiringCollector(self._n)

    def transition_observer_factory(self, t: "Transition") -> \
            Optional[TransitionIntervalPluginTransitionObserver]:
        """ Creates and returns a :class:`TransitionIntervalPluginTransitionObserver` instance."""
        return TransitionIntervalPluginTransitionObserver(self, t, self._clock, self._collector) \
            if self._transitions is None or t.ordinal in self._transitions else None