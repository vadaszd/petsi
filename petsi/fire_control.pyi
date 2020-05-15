#cython: language_level=3

import random
from collections import defaultdict
from functools import partial
from heapq import heappush, heappop
from itertools import count
from typing import TYPE_CHECKING, List, Set, Dict, Tuple, DefaultDict, Iterator, Callable

if TYPE_CHECKING:
    from . import Structure, Plugins

print("fire_control.pyx")


class FireControl:
    current_time: float

    def current_time_getter(self) -> Callable[[], float]:
        """ # noinspection PyUnresolvedReferences
            # return partial(FireControl.current_time.__get__, self)
        """

    def reset(self):
        """ Bring the fire control to its initial state.
        :return: None
        """

    def start(self):
        """ Call this method after the build of the Petri-net is finished and before the start of firening.
        :return: None
        """

    def enable_transition(self, transition: "Structure.Transition"):
        """ Callback method to indicate that a transition got enabled
        :param transition:
        :return:
        """

    def disable_transition(self, transition: "Structure.Transition"):
        """ Callback method to indicate that a transition got disabled
        :param transition:
        :return:
        """

    def _select_next_transition(self):
        """ Select the next transition to fire

            :raise IndexError   If there is no enabled transition
            :return             A (new_time, transition) tuple, indicating the simulation time of the transition and
                                the transitison itself.
        """

    def fire_next(self):
        """ Select and fire the next transition
        :return: None
        """


class SojournTimePluginTokenObserver(Plugins.AbstractTokenObserver["SojournTimerPlugin"]):
    # A function returning the current time
    _get_current_time: Callable[[], float]

    # The overall sojourn time of the observed token for each visited place
    _overall_sojourn_time: DefaultDict[str, float]

    _arrival_time: float

    def __init__(self, _plugin: "Plugins.Plugin", _token: "Structure.Token",
                 _get_current_time: Callable[[], float]):
        pass

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


class TokenCounterPluginPlaceObserver(Plugins.AbstractPlaceObserver["TokenCounterPlugin"]):
    # A function returning the current time
    _get_current_time: Callable[[], float]

    # Current number of tokens at the place
    _num_tokens: int

    # When the state of having _num_tokens tokens at the place was entered
    _time_of_last_token_move: float

    # Element i of this list contains the amount of time the place had i tokens
    # TODO: Use the Histogram class here as well
    _time_having: List[float]

    def __init__(self, p: "Structure.Place", _get_current_time: Callable[[], float]):
        pass

    def clear(self):pass

    @property
    def histogram(self) -> Iterator[float]:
        pass

    def report_arrival_of(self, token):
        pass

    def report_departure_of(self, token):
        pass

