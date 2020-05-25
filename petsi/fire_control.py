# cython: language_level=3
# cython: profile=False

from collections import defaultdict
from heapq import heappush, heappop
from itertools import count
from random import choices as random_choices
from typing import TYPE_CHECKING, List, Set, Dict, Tuple, Iterator

import cython

if TYPE_CHECKING:
    from . import Structure
    from .Plugins import Plugin


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


class AutoFirePluginTransitionObserver:

    def __init__(self, _plugin: "Plugin", _transition: "Structure.Transition",
                 _fire_control: "FireControl"):
        self._plugin = _plugin
        self._transition = _transition
        self._fire_control = _fire_control
        self._deadline = 0.0

    def got_enabled(self, ):
        self._fire_control.enable_transition(self._transition)

    def got_disabled(self, ):
        self._fire_control.disable_transition(self._transition)

    def reset(self): pass

    def after_firing(self): pass

    def before_firing(self): pass

