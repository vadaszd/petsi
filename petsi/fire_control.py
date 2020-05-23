# cython: language_level=3
# cython: profile=False
from .Plugins import Plugin

import cython
from random import choices as random_choices
from collections import defaultdict
from heapq import heappush, heappop
from itertools import count

from typing import TYPE_CHECKING, List, Set, Dict, Tuple, DefaultDict, Iterator

if TYPE_CHECKING:
    from . import Structure, Plugins

print("fire_control.py")


@cython.cclass
class _PriorityLevel:
    priority: int
    transitions: Set["Structure.Transition"]

    def __init__(self, priority: int):
        self.priority = priority
        self.transitions = set()

    def add(self, transition: "Structure.Transition"):
        self.transitions.add(transition)

    def remove(self, transition: "Structure.Transition"):
        self.transitions.remove(transition)

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __eq__(self, other):
        # if not isinstance(anything, _PriorityLevel):
        #     return NotImplemented
        return self.priority == other.priority

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __ne__(self, other):
        return self.priority != other.priority

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __lt__(self, other):
        return self.priority > other.priority

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __gt__(self, other):
        return self.priority < other.priority

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __le__(self, other):
        return self.priority >= other.priority

    @cython.locals(other="_PriorityLevel")
    @cython.returns(cython.bint)
    def __ge__(self, other):
        return self.priority <= other.priority


class Clock:
    _fire_control: "FireControl"

    def __init__(self, fire_control):
        self._fire_control = fire_control

    def read(self):
        return self._fire_control.current_time


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

    def get_clock(self) -> Clock:
        return Clock(self)

    def __init__(self):
        self._deadline_disambiguator = count()
        self._transition_enabled_at_start_up = dict()
        self.current_time = 0.0
        self._is_build_in_progress = True
        self._active_priority_levels = list()
        self._active_priorities = set()

        class PriorityLevelDict(defaultdict):
            def __missing__(self, priority):
                priority_level = self[priority] = _PriorityLevel(priority)
                return priority_level

        self._priority_levels = PriorityLevelDict()
        self._timed_transitions = list()

    def reset(self):
        # This will cause start() to re-enable the initially enabled transitions
        # based on _transition_enabled_at_start_up
        self.current_time = 0.0
        self._is_build_in_progress = True
        self._active_priority_levels.clear()
        self._active_priorities.clear()
        self._priority_levels.clear()
        self._timed_transitions.clear()

    def start(self):
        if self._is_build_in_progress:
            self._is_build_in_progress = False
            for transition, is_enabled in self._transition_enabled_at_start_up.items():
                if is_enabled:
                    self._enable_transition(transition)
                else:
                    "Nothing to do, by default all transitions are treated as disabled."

    def enable_transition(self, transition: "Structure.Transition"):
        if self._is_build_in_progress:
            self._transition_enabled_at_start_up[transition] = True
        else:
            self._enable_transition(transition)

    def disable_transition(self, transition: "Structure.Transition"):
        if self._is_build_in_progress:
            self._transition_enabled_at_start_up[transition] = False
        else:
            self._disable_transition(transition)

    def _schedule_timed_transition(self, transition: "Structure.Transition"):
        deadline: float = self.current_time + transition.get_duration()
        heappush(self._timed_transitions, (deadline, next(self._deadline_disambiguator), transition))

    def _remove_timed_transition_from_schedule(self, transition: "Structure.Transition"):
        assert self._next_timed_transition() is transition, \
            "Wow... cancelling a timed Transition before firing it..."
        heappop(self._timed_transitions)

    def _enable_transition(self, transition: "Structure.Transition"):
        if transition.is_timed:
            self._schedule_timed_transition(transition)
        else:
            priority: int = transition.priority
            priority_level: _PriorityLevel = self._priority_levels[priority]
            priority_level.add(transition)
            if priority not in self._active_priorities:
                heappush(self._active_priority_levels, priority_level)
                self._active_priorities.add(priority)

    def _disable_transition(self, transition: "Structure.Transition"):
        if transition.is_timed:
            self._remove_timed_transition_from_schedule(transition)
        else:
            priority = transition.priority
            assert priority in self._active_priorities, "Wow... "
            priority_level = self._priority_levels[priority]
            priority_level.remove(transition)
            # It would be too expensive to remove a just emptied priority_level from
            # the _active_priority_levels heap, so we do not do that. We wait until
            # it gets to the front of the heap and remove it then.

    def _next_timed_transition(self):
        return self._timed_transitions[0][-1]

    def _select_next_transition(self):
        """ Select and fire the next transition

            :raise IndexError   If there is no enabled transition
        """

        # First try to find an enabled immediate transition
        while len(self._active_priority_levels) > 0:
            priority_level = self._active_priority_levels[0]
            num_transitions = len(priority_level.transitions)

            if num_transitions == 0:
                heappop(self._active_priority_levels)
                self._active_priorities.remove(priority_level.priority)
                continue

            weights = list()
            for transition in priority_level.transitions:
                weights.append(transition.weight)

            transition = random_choices(list(priority_level.transitions), weights)[0]
            new_time = self.current_time

            # No need to remove the transition from the priority_level.
            # The got_disabled callback will do that, be there need,
            # during the firing of the transition.

            # The else clause of the loop will not be executed, as the
            # loop condition still holds!
            break
        else:
            # The _active_priority_levels heap is empty.
            # There is no enabled immediate transition, so we try a timed one
            # Will raise an IndexError if there is no enabled timed transition
            new_time, _, transition = self._timed_transitions[0]

        return new_time, transition

    def fire_next(self):
        new_time, transition = self._select_next_transition()
        # print(new_time, transition.name)
        self.current_time = new_time
        transition.fire()

        # Timed transitions that remained enabled after firing them
        # need to be re-scheduled.
        if transition.is_timed and transition.is_enabled:
            self._remove_timed_transition_from_schedule(transition)
            self._schedule_timed_transition(transition)


class SojournTimePluginTokenObserver:

    def __init__(self, _plugin: "Plugins.Plugin", _token: "Structure.Token",
                 _clock: Clock):
        self._plugin = _plugin
        self._token = _token
        self._clock = _clock
        self._overall_sojourn_time: DefaultDict[str, float] = defaultdict(lambda: 0.0)
        self._arrival_time = 0.0

    def reset(self):
        # The observed token will anyway be removed, together with us...
        pass

    def report_construction(self):
        pass

    def report_destruction(self):
        """ For each visited place, select the overall s.t. histogram bucket
            based on accumulated time and increment the bucket.
        """
        for place_name, sojourn_time in self._overall_sojourn_time.items():
            self._plugin.overall_histogram(place_name).add(sojourn_time)

    def report_arrival_at(self, _: "Structure.Place"):
        """ Start timer for place"""
        self._arrival_time = self._clock.read()

    def report_departure_from(self, p: "Structure.Place"):
        """ Stop timer and compute the sojourn time.
            Select the bucket of the per visit histogram that belongs
            to the place and increment it.
            Add s.t. for the overall sojourn time of the token for this place
        """
        current_time: float = self._clock.read()
        sojourn_time: float = current_time - self._arrival_time
        sojourn_time_py: object = sojourn_time
        self._plugin.per_visit_histogram(p.name).add(sojourn_time_py)
        self._overall_sojourn_time[p.name] += sojourn_time_py


class TokenCounterPluginPlaceObserver:

    def __init__(self, _plugin: Plugin, _place: "Structure.Place", _clock: Clock):
        self._plugin = _plugin
        self._place = _place
        self._clock = _clock
        self._num_tokens = 0
        self._time_of_last_token_move = 0.0
        self._time_having: List[float] = list()

    def reset(self):
        self._time_having.clear()
        self._num_tokens = 0
        self._time_of_last_token_move = 0.0

    @property
    def histogram(self) -> Iterator[float]:
        total_time = sum(self._time_having)
        return (t / total_time for t in self._time_having)

    def _update_num_tokens_by(self, delta: int):
        now: float = self._clock.read()
        duration: float = now - self._time_of_last_token_move

        try:
            self._time_having[self._num_tokens] += duration
        except IndexError:
            # Off by at most one
            assert len(self._time_having) == self._num_tokens
            self._time_having.append(duration)

        self._time_of_last_token_move = now
        self._num_tokens += delta
        # Cannot go negative
        assert self._num_tokens >= 0

    def report_arrival_of(self, token):
        self._update_num_tokens_by(+1)

    def report_departure_of(self, token):
        self._update_num_tokens_by(-1)



