from . import Plugins

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Set, Dict, Tuple, DefaultDict, Callable, Iterator
from more_itertools import consume
from collections import defaultdict
from heapq import heappush, heappop
from itertools import repeat
import random

if TYPE_CHECKING:
    from . import Structure

""" This module contains a plugin that fires enabled transitions according to the below ordering rules.

    0. We track a global current time, initialized to a user-provided value.
    
    1. No transition can fire if another transition with a higher priority is enabled.
    
    2. If more than one transition is enabled on the highest priority level (immediate transitions), then:
    
        a) If the priority level is positive, then a transition is chosen randomly, according to the weights
            of the enabled transitions
            
        b) On priority level 0 (timed transitions) the one with the shortest deadline is chosen. 
            The deadline is computed when the transition gets enabled. It is the current time plus 
            a sample taken from the duration distribution associated with the transition.
            
    3. Firing a timed transition sets the current time to the deadline of the fired transition.
    
    4. The underlying Petri net guarantees that a timed transition, once enabled, will not get disabled
        without firing the transition.
"""


@dataclass(eq=False)
class AutoFirePlugin(Plugins.AbstractPlugin):
    """ A PetSi plugin for firing transitions automatically.

        The transitions are selected for firing based on the rules for
        Extended Stochastic Petri Nets.
    """

    @dataclass(eq=False)
    class FireControl:
        current_time: float = field(default=0.0)

        # A heap of (priority, Transition set) tuples, ordered by negative priority.
        # This is needed as the head of the heap (in the Python implementation) is
        # the smallest item. Each set contains the enabled immediate transitions at
        # that level. Empty sets are removed from the head of the heap.
        # Below these sets are also called the 'priority_level'.
        _active_priority_levels: List[Tuple[int, Set["Structure.Transition"]]] = field(default_factory=list, init=False)

        # The set of priorities with priority levels present in the _active_priority_levels heap
        _active_priorities: Set[int] = field(default_factory=set, init=False)

        # The same set of Transitions as above (same set object!), keyed by priority,
        # allowing random access. The sets are created when the observer for
        # the first transition at that priority is created
        # and are never removed from this dict.
        _priority_levels: DefaultDict[int, Set["Structure.Transition"]] = field(
            default_factory=lambda: defaultdict(set))

        # A heap of (deadline, Transition) tuples, ordered by deadline
        _timed_transitions: List[Tuple[float, "Structure.Transition"]] = field(default_factory=list, init=False)

        def enable_transition(self, transition: "Structure.Transition"):
            if transition.is_timed:
                deadline = self.current_time + transition.get_duration()
                heappush(self._timed_transitions, (deadline, transition))
            else:
                priority = transition.priority
                priority_level = self._priority_levels[priority]
                priority_level.add(transition)
                if priority not in self._active_priorities:
                    heappush(self._active_priority_levels, (-priority, priority_level))
                    self._active_priorities.add(priority)

        def disable_transition(self, transition: "Structure.Transition"):
            if transition.is_timed:
                assert self._next_timed_transition() is transition, "Wow.... disabling a timed Transition..."
                heappop(self._timed_transitions)
            else:
                priority = transition.priority
                assert priority in self._active_priorities, "Wow... "
                self._priority_levels[priority].remove(transition)
                # It would be too expensive to remove a just emptied priority_level from
                # the _active_priority_levels heap, so we do not do that. We wait until
                # it gets to the front of the heap and remove it then.

        def _next_timed_transition(self):
            return self._timed_transitions[0][1]

        def select_next_transition(self):
            """ Select and fire the next transition

                :raise IndexError   If there is no enabled transition
            """
            # First try to find an enabled immediate transition
            while len(self._active_priority_levels) > 0:
                negative_priority, priority_level = self._active_priority_levels[0]
                num_transitions = len(priority_level)

                if num_transitions == 0:
                    heappop(self._active_priority_levels)
                    self._active_priorities.remove(-negative_priority)
                    continue

                weights = [t.weight for t in priority_level]
                transition = random.choices(list(priority_level), weights)[0]
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
                new_time, transition = self._timed_transitions[0]

            return new_time, transition

        def fire_next(self):
            new_time, transition = self._fire_control.select_next_transition()
            transition.fire()
            self.current_time = new_time

    _fire_control: FireControl = field(default_factory=FireControl, init=False)

    @property
    def current_time(self):
        return self._fire_control.current_time

    def fire_until(self, end_time: float):
        while self.current_time < end_time:
            self._fire_control.fire_next()

    def fire_repeatedly(self, count: int = 0):
        # noinspection Mypy - complains about repeat(..., None)
        consume(repeat(lambda _: self._fire_control.fire_next(), None if count == 0 else count))

    def place_observer_factory(self, p: "Structure.Place") -> Optional[Plugins.PlaceObserver]:
        return None  # PlaceObserver(p)

    def token_observer_factory(self, t: "Structure.Token") -> Optional[Plugins.TokenObserver]:
        return None  # TokenObserver(t)

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional[Plugins.TransitionObserver]:
        return self.TransitionObserver(t, self._fire_control)

    @dataclass(eq=False)
    class TransitionObserver(Plugins.TransitionObserver):
        _transition: "Structure.Transition"
        _fire_control: "AutoFirePlugin.FireControl"

        def got_enabled(self, ):
            self._fire_control.enable_transition(self._transition)

        def got_disabled(self, ):
            self._fire_control.disable_transition(self._transition)

        def before_firing(self, ): pass

        def after_firing(self, ): pass


@dataclass(eq=False)
class TokenCounterPlugin(Plugins.AbstractPlugin):
    """ A PetSi plugin providing by-place token-count stats

        The plugin collects the empirical distribution of the
        time-weighted token counts at all places of the observed Petri net,
        i.e. in what percentage of time the token count is i at place j.
    """

    # A function returning the current time
    _get_current_time: Callable[[], float]

    def histogram(self, place_name: str) -> Iterator[float]:
        return self._place_observers[place_name].histogram

    def place_observer_factory(self, p: "Structure.Place") -> Optional["PlaceObserver"]:
        o = self._place_observers[p.name] = self.PlaceObserver(p, self._get_current_time)
        return o

    def token_observer_factory(self, t: "Structure.Token") -> Optional[Plugins.TokenObserver]:
        return None  # TokenObserver(t)

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional[Plugins.TransitionObserver]:
        return None  # TransitionObserver(t)

    @dataclass(eq=False)
    class PlaceObserver(Plugins.PlaceObserver):
        place: "Structure.Place"

        # A function returning the current time
        _get_current_time: Callable[[], float]

        # Current number of tokens at the place
        _num_tokens: int = field(default=0, init=False)

        # When the state of having _num_tokens tokens at the place was entered
        _time_of_last_token_move: float = field(default=0.0, init=False)

        # Element i of this list contains the amount of time the place had i tokens
        _time_having: List[float] = field(default_factory=list, init=False)

        @property
        def histogram(self) -> Iterator[float]:
            total_time = sum(self._time_having)
            return (t/total_time for t in self._time_having)

        def _update_num_tokens_by(self, delta):
            now = self._get_current_time()
            duration = now - self._time_of_last_token_move

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



# @dataclass(eq=False)
# class TokenObserver(Plugins.TokenObserver):
#     token: "Structure.Token"
#     creationTime: float = field(init=False)
#     arrivalTime: float = field(init=False)
#
#     def report_construction(self, ): pass
#
#     def report_destruction(self, ): pass
#
#     def report_arrival_at(self, p: "Structure.Place"): pass
#
#     def report_departure_from(self, p: "Structure.Place"): pass

# AutoFirePlugin *-- "*" TransitionObserver
# AutoFirePlugin *-- "*" TokenObserver
# AutoFirePlugin *-- "*" PlaceObserver
# AutoFirePlugin ..|> Plugins.AbstractPlugin
# TransitionObserver ..|> Plugins.TransitionObserver
# TokenObserver ..|> Plugins.TokenObserver
# PlaceObserver ..|> Plugins.PlaceObserver
