#cython: language_level=3

from typing import TYPE_CHECKING, List, Set, Dict, Tuple, DefaultDict, Iterator, Callable

if TYPE_CHECKING:
    from . import Structure, Plugins


class _PriorityLevel:
    priority: int
    transitions: Set["Structure.Transition"]

    def __init__(self, priority: int): pass
    def add(self, transition: "Structure.Transition"): pass

    def remove(self, transition: "Structure.Transition"): pass

    def __eq__(self, other: "_PriorityLevel") -> bool: pass
    def __ne__(self, other: "_PriorityLevel") -> bool: pass
    def __lt__(self, other: "_PriorityLevel") -> bool: pass
    def __gt__(self, other: "_PriorityLevel") -> bool: pass
    def __le__(self, other: "_PriorityLevel") -> bool: pass
    def __ge__(self, other: "_PriorityLevel") -> bool: pass

class Clock:
    _fire_control: "FireControl"

    def __init__(self, fire_control: "FireControl"):
        pass

    def read(self) -> float:
        pass

class FireControl:
    current_time: float
    _is_build_in_progress: bool

    _deadline_disambiguator: Iterator[int]
    _transition_enabled_at_start_up: Dict["Structure.Transition", bool]

    # A heap of (priority, Transition set) tuples, ordered by negative priority.
    # This is needed as the head of the heap (in the Python implementation) is
    # the smallest item. Each set contains the enabled immediate transitions at
    # that level. Empty sets are removed from the head of the heap.
    # Below these sets are also called the 'priority_level'.
    _active_priority_levels: List[_PriorityLevel]

    # The set of priorities with priority levels present in the _active_priority_levels heap
    _active_priorities: Set[int]

    # The same set of Transitions as above (same set object!), keyed by priority,
    # allowing random access. The sets are created when the observer for
    # the first transition at that priority is created
    # and are never removed from this dict.
    _priority_levels: Dict[int, _PriorityLevel]

    # A heap of (deadline, Transition) tuples, ordered by deadline
    _timed_transitions: List[Tuple[float, int, "Structure.Transition"]]

    def get_clock(self) -> Clock: pass

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

    def _enable_transition(self, transition: "Structure.Transition"): pass
    def _disable_transition(self, transition: "Structure.Transition"): pass
    def _next_timed_transition(self) -> "Structure.Transition": pass
    def _schedule_timed_transition(self, transition: "Structure.Transition"): pass
    def _remove_timed_transition_from_schedule(self, transition: "Structure.Transition"): pass
    def _select_next_transition(self): pass

    def fire_next(self):
        """ Select and fire the next transition
        :return: None
        """


class SojournTimePluginTokenObserver(Plugins.AbstractTokenObserver["SojournTimePlugin"]):
    _plugin: Plugins.Plugin
    _token: "Structure.Token"

    # A function returning the current time
    _clock: Clock

    # The overall sojourn time of the observed token for each visited place
    _overall_sojourn_time: DefaultDict[str, float]

    _arrival_time: float

    def __init__(self, _plugin: "Plugins.Plugin", _token: "Structure.Token", _clock: Clock):
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


class TokenCounterPluginPlaceObserver(Plugins.AbstractPlaceObserver["TokenCounterPlugin"]):
    _plugin: Plugins.Plugin
    _place: "Structure.Place"

    # Access to the current time
    _clock: Clock

    # Current number of tokens at the place
    _num_tokens: int

    # When the state of having _num_tokens tokens at the place was entered
    _time_of_last_token_move: float

    # Element i of this list contains the amount of time the place had i tokens
    # TODO: Use the Histogram class here as well
    _time_having: List[float]

    def __init__(self, _plugin: Plugins.Plugin, p: "Structure.Place", _clock: Clock):
        pass

    def reset(self):pass

    @property
    def histogram(self) -> Iterator[float]:
        pass

    def report_arrival_of(self, token):
        pass

    def report_departure_of(self, token):
        pass

    def _update_num_tokens_by(self, delta: int): pass