#cython: language_level=3

import random
from collections import defaultdict
from functools import partial
from heapq import heappush, heappop
from itertools import count
from typing import TYPE_CHECKING, List, Set, Dict, Tuple, DefaultDict, Iterator, Callable

if TYPE_CHECKING:
    from . import Structure

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