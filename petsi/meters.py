""" Plugins for collecting statistics on the activities in a Petri net.
"""

from array import array
from dataclasses import dataclass, field
from itertools import count
from typing import Generic, Optional, FrozenSet, Dict, Callable, Iterator, TYPE_CHECKING

from .Plugins import APlaceObserver, ATransitionObserver, ATokenObserver, AbstractPlugin, NoopTransitionObserver, \
    NoopTokenObserver, NoopPlaceObserver
from ._autofire import Clock
from ._meters import ACollector, TokenCounterCollector, TokenCounterPluginPlaceObserver, SojournTimeCollector, \
    SojournTimePluginTokenObserver, FiringCollector, TransitionIntervalPluginTransitionObserver

if TYPE_CHECKING:
    from ._structure import Token, Place


@dataclass(eq=False)
class _MeterPlugin(Generic[ACollector, APlaceObserver, ATransitionObserver, ATokenObserver],  #
                   AbstractPlugin[APlaceObserver, ATransitionObserver, ATokenObserver],
                   ):
    """ Base class for plugins collecting observations."""
    _n: int                                     # number of observations to collect
    _places: Optional[FrozenSet[int]]           # Observe these places only
    _token_types: Optional[FrozenSet[int]]      # Observe these token types only
    _transitions: Optional[FrozenSet[int]]      # Observe these transitions only
    _clock: Clock

    _collector: ACollector = field(init=False)

    def get_observations(self) -> Dict[str, array]:
        return self._collector.get_observations()

    def get_need_more_observations(self) -> Callable[[], bool]:
        return self._collector.need_more_observations

    @property
    def required_observations(self) -> int:
        return self._collector.required_observations

    @required_observations.setter
    def required_observations(self, required_observations: int):
        self._collector.required_observations = required_observations


@dataclass(eq=False)
class TokenCounterPlugin(
        _MeterPlugin[TokenCounterCollector, TokenCounterPluginPlaceObserver,
                     NoopTransitionObserver, NoopTokenObserver]):

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


@dataclass(eq=False)
class SojournTimePlugin(
        _MeterPlugin[SojournTimeCollector, "NoopPlaceObserver", "NoopTransitionObserver",
                     SojournTimePluginTokenObserver]):
    """ A PetSi plugin providing by-place sojourn time stats

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


@dataclass(eq=False)
class TransitionIntervalPlugin(
        _MeterPlugin[FiringCollector,
                     NoopPlaceObserver, TransitionIntervalPluginTransitionObserver, NoopTokenObserver]):
    """ A PetSi plugin for collecting stats on the time intervals between firings of transitions."""

    def __post_init__(self):
        self._collector = FiringCollector(self._n)

    def transition_observer_factory(self, t: "Transition") -> \
            Optional[TransitionIntervalPluginTransitionObserver]:

        return TransitionIntervalPluginTransitionObserver(self, t, self._clock, self._collector) \
            if self._transitions is None or t.ordinal in self._transitions else None