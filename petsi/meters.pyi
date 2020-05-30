from array import array
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, List, Iterator, Sequence, FrozenSet, Optional, Dict

from . import Plugins
from .Plugins import Plugin
from .Structure import Place
from .fire_control import Clock

if TYPE_CHECKING:
    from . import Structure


class GenericCollector:
    required_observations: int
    _type_codes: Dict[str, str]
    _arrays: Dict[str, array]
    _any_array: array

    def __init__(self, required_observations: int): pass

    def reset(self): pass

    def get_observations(self) -> Dict[str, array]:
        pass

    def need_more_observations(self) -> bool: pass

class TokenCounterCollector(GenericCollector):
    _start_time: array
    _place: array
    _count: array
    _duration: array

    def collect(self, start_time: float, place: int, count: int, duration: float): pass


class TokenCounterPluginPlaceObserver(Plugins.AbstractPlaceObserver["TokenCounterPlugin"]):

    _plugin: Plugin
    _place: Place

    # Access to the current time
    _clock: Clock
    _collector: TokenCounterCollector

    # Current number of tokens at the place
    _num_tokens: int

    # When the state of having _num_tokens tokens at the place was entered
    _time_of_last_token_move: float

    def __init__(self, _plugin: Plugin, _place: "Structure.Place", _clock: Clock,
                 _collector: TokenCounterCollector): pass

    def reset(self): pass

    @property
    def histogram(self) -> Iterator[float]:
        """ The Nth element of the returned iterator is the time the number of tokens at the place was N """

    def _update_num_tokens_by(self, delta: int): pass

    def report_arrival_of(self, token): pass

    def report_departure_of(self, token): pass


class SojournTimeCollector(GenericCollector):
    _token_id: array
    _token_type: array
    _start_time: array
    _num_transitions: array
    _place: array
    _duration: array

    def reset(self): pass

    def collect(self, token_id: int, token_type: int, start_time: float, num_transitions: int, place: int, duration: float):
        pass

class SojournTimePluginTokenObserver(Plugins.AbstractTokenObserver["SojournTimePlugin"]):
    _plugin: Plugins.Plugin
    _token: "Structure.Token"
    _token_id: int
    _transition_count: int

    _places: Optional[FrozenSet[int]]

    _clock: Clock

    # The overall sojourn time of the observed token for each visited place
    _collector: SojournTimeCollector

    _arrival_time: float

    def __init__(self, _plugin: "Plugins.Plugin", _token: "Structure.Token",
                 _places: Optional[FrozenSet[int]], _clock: Clock, _collector: SojournTimeCollector, _token_id: int):
        pass

    def reset(self): pass

    def report_construction(self): pass

    def report_destruction(self):
        """ For each visited place, select the overall s.t. histogram bucket
            based on accumulated time and increment the bucket.
        """

    def report_arrival_at(self, p: "Structure.Place"):
        """ Start timer for place"""

    def report_departure_from(self, p: "Structure.Place"):
        """ Stop timer and compute the sojourn time.
            Select the bucket of the per visit histogram that belongs
            to the place and increment it.
            Add s.t. for the overall sojourn time of the token for this place
        """


class FiringCollector(GenericCollector):

    _transition: array   # ('L', ) unsigned long (32 bits)
    _firing_time: array  # ('d', ) double
    _interval: array     # ('d', ) double

    def collect(self, transition: int, firing_time: float, interval: float): pass


class TransitionIntervalPluginTransitionObserver(Plugins.NoopTransitionObserver["TransitionIntervalPlugin"]):

    _collector: FiringCollector
    _previous_firing_time: float = field(init=False)

    def __init__(self, _plugin: "Plugins.Plugin", _transition: "Structure.Transition", _clock: Clock,
                 _collector: FiringCollector): pass


