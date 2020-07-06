""" A plugin that collects by-place token-count stats.

.. rubric:: Public package interface

- Class :class:`TokenCounterPlugin` (see below)

.. rubric:: Internal submodules

.. autosummary::
    :template: module_reference.rst
    :recursive:
    :toctree:

    petsi.plugins.tokencounter._tokencounter
"""
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from ...util import export

from ..meters import MeterPlugin
from ._tokencounter import TokenCounterCollector, TokenCounterPluginPlaceObserver

if TYPE_CHECKING:
    from ..interface import NoopTokenObserver, NoopTransitionObserver
    from ..._structure import Place


@export
@dataclass(eq=False)
class TokenCounterPlugin(
        MeterPlugin["TokenCounterCollector", "TokenCounterPluginPlaceObserver",
                    "NoopTransitionObserver", "NoopTokenObserver"]):

    """ A PetSi plugin providing by-place token-count stats

        The plugin collects the empirical distribution of the
        time-weighted token counts at all places of the observed Petri net,
        i.e. in what percentage of time the token count is i at place j.
    """

    def __post_init__(self):
        self._collector = TokenCounterCollector(self._n)

    def place_observer_factory(self, p: "Place") -> Optional[TokenCounterPluginPlaceObserver]:
        return TokenCounterPluginPlaceObserver(self, p, self._clock, self._collector) \
            if self._places is None or p.ordinal in self._places else None
