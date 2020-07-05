""" A plugin that collects by-place sojourn time stats.

.. rubric:: Public package interface

- Class :class:`SojournTimePlugin` (see below)

.. rubric:: Internal submodules

.. autosummary::
    :template: module_reference.rst
    :recursive:
    :toctree:

    petsi.plugins.sojourntime._sojourntime
"""

from dataclasses import dataclass, field
from itertools import count
from typing import Iterator, Optional, TYPE_CHECKING

from ...util import export

from ..meters import MeterPlugin
from ._sojourntime import SojournTimeCollector, SojournTimePluginTokenObserver

if TYPE_CHECKING:
    from ..Plugins import NoopPlaceObserver, NoopTransitionObserver
    from ..._structure import Token


@export
@dataclass(eq=False)
class SojournTimePlugin(
        MeterPlugin["SojournTimeCollector", "NoopPlaceObserver", "NoopTransitionObserver",
                    "SojournTimePluginTokenObserver"]):
    """ A PetSi plugin providing by-place sojourn time stats.

        The plugin collects the empirical distribution of the
        time a token spends at each place of the observed Petri net,
        i.e. in what percentage of the tokens seen was the per-visit and overall time
        spent by the token at place j in bucket i of the histogram.

        On the per-visit histograms each stay is translated into a separate increment.
        The bucket is selected based on the time the token spent at the place during a single visit.

        On the overall histograms one increment represents all the visits of a token at a given place.
        The bucket is selected based on the cumulative time the token spent at the place during its whole life.
    """

    token_id: Iterator[int] = field(default_factory=count, init=False)

    def __post_init__(self):
        self._collector = SojournTimeCollector(self._n)

    def token_observer_factory(self, t: "Token") -> Optional[SojournTimePluginTokenObserver]:
        return SojournTimePluginTokenObserver(self, t, self._places, self._clock,
                                              self._collector, next(self.token_id)) \
            if self._token_types is None or t.typ.ordinal in self._token_types else None


