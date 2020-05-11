import random
from bisect import bisect
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps, cached_property
from heapq import heappush, heappop
from itertools import repeat, count
from typing import TYPE_CHECKING, Optional, List, Set, Dict, Tuple, DefaultDict, Callable, Iterator, TypeVar, Any, cast, \
    Sequence

from . import Plugins
from .Plugins import NoopTokenObserver, NoopTransitionObserver, NoopPlaceObserver
from .Structure import foreach, Net

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
class AutoFirePlugin(
        Plugins.AbstractPlugin[NoopPlaceObserver, "AutoFirePlugin.TransitionObserver", NoopTokenObserver]):

    """ A PetSi plugin for firing transitions automatically.

        The transitions are selected for firing based on the rules for
        Extended Stochastic Petri Nets.
    """

    @dataclass(eq=False)
    class FireControl:
        current_time: float = field(default=0.0)

        _deadline_disambiguator: Iterator[int] = field(default_factory=count, init=False)

        _is_build_in_progress: bool = field(default=True, init=False)
        _transition_enabled_at_start_up: Dict["Structure.Transition", bool] = field(default_factory=dict, init=False)

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
        _timed_transitions: List[Tuple[float, int, "Structure.Transition"]] = field(default_factory=list, init=False)

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
            deadline = self.current_time + transition.get_duration()
            heappush(self._timed_transitions, (deadline, next(self._deadline_disambiguator), transition))

        def _remove_timed_transition_from_schedule(self, transition: "Structure.Transition"):
            assert self._next_timed_transition() is transition, \
                "Wow... cancelling a timed Transition before firing it..."
            heappop(self._timed_transitions)

        def _enable_transition(self, transition: "Structure.Transition"):
            if transition.is_timed:
                self._schedule_timed_transition(transition)
            else:
                priority = transition.priority
                priority_level = self._priority_levels[priority]
                priority_level.add(transition)
                if priority not in self._active_priorities:
                    heappush(self._active_priority_levels, (-priority, priority_level))
                    self._active_priorities.add(priority)

        def _disable_transition(self, transition: "Structure.Transition"):
            if transition.is_timed:
                self._remove_timed_transition_from_schedule(transition)
            else:
                priority = transition.priority
                assert priority in self._active_priorities, "Wow... "
                self._priority_levels[priority].remove(transition)
                # It would be too expensive to remove a just emptied priority_level from
                # the _active_priority_levels heap, so we do not do that. We wait until
                # it gets to the front of the heap and remove it then.

        def _next_timed_transition(self):
            return self._timed_transitions[0][-1]

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
                new_time, _, transition = self._timed_transitions[0]

            return new_time, transition

        def fire_next(self):
            new_time, transition = self.select_next_transition()
            # print(new_time, transition.name)
            self.current_time = new_time
            transition.fire()

            # Timed transitions that remained enabled after firing them
            # need to be re-scheduled.
            if transition.is_timed and transition.is_enabled:
                self._remove_timed_transition_from_schedule(transition)
                self._schedule_timed_transition(transition)

    _fire_control: FireControl = field(default_factory=FireControl, init=False)

    def get_current_time(self):
        return self._fire_control.current_time

    current_time = property(get_current_time)

    def reset(self): self._fire_control.reset()

    def fire_until(self, end_time: float):
        self._fire_control.start()

        while self.current_time < end_time:
            self._fire_control.fire_next()

    def fire_repeatedly(self, count_of_firings: int = 0):
        self._fire_control.start()

        foreach(lambda _: self._fire_control.fire_next(),
                repeat(None) if count_of_firings == 0 else repeat(None, count_of_firings))

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional["AutoFirePlugin.TransitionObserver"]:
        return self.TransitionObserver(self, t, self._fire_control)

    @dataclass(eq=False)
    class TransitionObserver(Plugins.AbstractTransitionObserver["AutoFirePlugin"]):
        _fire_control: "AutoFirePlugin.FireControl"
        _deadline: float = field(default=0.0, init=False)

        def got_enabled(self, ):
            self._fire_control.enable_transition(self._transition)

        def got_disabled(self, ):
            self._fire_control.disable_transition(self._transition)

        def before_firing(self, ): pass

        def after_firing(self, ): pass


@dataclass(eq=False)
class TokenCounterPlugin(
        Plugins.AbstractPlugin["TokenCounterPlugin.PlaceObserver", NoopTransitionObserver, NoopTokenObserver]):

    """ A PetSi plugin providing by-place token-count stats

        The plugin collects the empirical distribution of the
        time-weighted token counts at all places of the observed Petri net,
        i.e. in what percentage of time the token count is i at place j.

        :arg _get_current_time   A callable returning the current simulation time
    """

    # A function returning the current time
    _get_current_time: Callable[[], float]

    def clear(self):
        """ Clear the state of the plugin. Removes all data collected during the previous simulation.
        """
        for place_observer in self._place_observers.values():
            place_observer.clear()

    def histogram(self, place_name: str) -> Iterator[float]:
        return self._place_observers[place_name].histogram

    def place_observer_factory(self, p: "Structure.Place") -> Optional["PlaceObserver"]:
        return self.PlaceObserver(self, p, self._get_current_time)

    @dataclass(eq=False)
    class PlaceObserver(Plugins.AbstractPlaceObserver["TokenCounterPlugin"]):
        # A function returning the current time
        _get_current_time: Callable[[], float]

        # Current number of tokens at the place
        _num_tokens: int = field(default=0, init=False)

        # When the state of having _num_tokens tokens at the place was entered
        _time_of_last_token_move: float = field(default=0.0, init=False)

        # Element i of this list contains the amount of time the place had i tokens
        # TODO: Use the Histogram class here as well
        _time_having: List[float] = field(default_factory=list, init=False)

        def clear(self):
            self._time_having.clear()
            self._num_tokens = 0
            self._time_of_last_token_move = 0.0

        @property
        def histogram(self) -> Iterator[float]:
            total_time = sum(self._time_having)
            return (t / total_time for t in self._time_having)

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


@dataclass(eq=False)
class SojournTimePlugin(Plugins.AbstractPlugin):
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

    @dataclass(eq=False)
    class Histogram:
        _bucket_boundaries: Sequence[float]
        _buckets: List[int] = field(init=False)
        _min_value: float = field(default=0.0, init=False)
        _max_value: float = field(default=0.0, init=False)
        _sum_value: float = field(default=0.0, init=False)

        def __post_init__(self):
            self._buckets = list(repeat(0, len(self._bucket_boundaries) + 1))

        def __iter__(self) -> Iterator[float]:
            num_values_total = float(self.num_values)
            for bucket_values in self._buckets:
                yield bucket_values / num_values_total

        def __len__(self):
            return self.num_values

        def add(self, value: float):
            """ Increment the count of elements in the bucket value belongs to """
            i = bisect(self._bucket_boundaries, value)
            self._buckets[i] += 1

            self._sum_value += value

            if self._min_value > value or self._min_value == 0.0:
                self._min_value = value

            if self._max_value < value or self._max_value == 0.0:
                self._max_value = value

        @property
        def min(self):
            return self._min_value

        @property
        def max(self):
            return self._max_value

        @property
        def mean(self):
            return self._sum_value / self.num_values

        @cached_property
        def num_values(self):
            """ :returns The number of items addedd to the histogram.

                Caveat!!! Only call this function after adding all items to the histogram,
                as the return value is cached and not recalculated for subsequent invocations.
             """
            return sum(self._buckets)

    # A function returning the current time
    _get_current_time: Callable[[], float]

    bucket_boundaries_per_visit: Sequence[float] = field(default=(), init=False)
    bucket_boundaries_overall: Sequence[float] = field(default=(), init=False)

    _per_visit_histograms: Dict["Structure.TokenType", Histogram] = field(init=False)

    # A s.t. histogram for each place
    _overall_histograms: Dict["Structure.TokenType", Histogram] = field(init=False)

    def clear(self):
        """ Clear the state of the plugin.

        Removes all token observers and the data collected during the previous simulation.
        """
        self._per_visit_histograms.clear()
        self._overall_histograms.clear()
        self._token_observers.clear()

    def per_visit_histogram(self, place_name) -> Histogram:
        return self._per_visit_histograms[place_name]

    def overall_histogram(self, place_name) -> Histogram:
        return self._overall_histograms[place_name]

    def __post_init__(self):
        self._per_visit_histograms = defaultdict(self._new_per_visit_histogram)
        self._overall_histograms = defaultdict(self._new_overall_histogram)

    def _new_per_visit_histogram(self):
        return self.Histogram(self.bucket_boundaries_per_visit)

    def _new_overall_histogram(self):
        return self.Histogram(self.bucket_boundaries_overall)

    def token_observer_factory(self, t: "Structure.Token") -> Optional["TokenObserver"]:
        return self.TokenObserver(self, t, self._get_current_time)

    @dataclass(eq=False)
    class TokenObserver(Plugins.AbstractTokenObserver["SojournTimerPlugin"]):
        # A function returning the current time
        _get_current_time: Callable[[], float]

        # The overall sojourn time of the observed token for each visited place
        _overall_sojourn_time: DefaultDict[str, float] = field(default_factory=lambda: defaultdict(lambda: 0.0))

        _arrival_time: float = field(default=0.0, init=False)

        def report_construction(self):
            pass

        def report_destruction(self):
            """ For each visited place, select the overall s.t. histogram bucket
                based on accumulated time and increment the bucket.
            """
            for place_name, sojourn_time in self._overall_sojourn_time.items():
                self._plugin.overall_histogram(place_name).add(sojourn_time)

        def report_arrival_at(self, p: "Structure.Place"):
            """ Start timer for place"""
            self._arrival_time = self._get_current_time()

        def report_departure_from(self, p: "Structure.Place"):
            """ Stop timer and compute the sojourn time.
                Select the bucket of the per visit histogram that belongs
                to the place and increment it.
                Add s.t. for the overall sojourn time of the token for this place
            """
            sojourn_time = self._get_current_time() - self._arrival_time
            self._plugin.per_visit_histogram(p.name).add(sojourn_time)
            self._overall_sojourn_time[p.name] += sojourn_time


class TransitionFrequencyPlugin(Plugins.AbstractPlugin):
    pass


class Simulator:
    def __init__(self, net_name: str = "net"):
        self._net = Net(net_name)
        self._auto_fire = AutoFirePlugin("auto-fire plugin")
        self._net.register_plugin(self._auto_fire)
        self._token_counter = TokenCounterPlugin("token counter plugin", self._auto_fire.get_current_time)
        self._net.register_plugin(self._token_counter)
        self._sojourn_time = SojournTimePlugin("sojourn time plugin", self._auto_fire.get_current_time,)
        self._net.register_plugin(self._sojourn_time)

    @property
    def net(self) -> "Structure.Net": return self._net

    _FuncType = Callable[..., Any]
    _F = TypeVar('_F', bound=_FuncType)

    # noinspection Mypy,PyMethodParameters
    def _delegate_to(f: _F) -> _F:
        @wraps(f)
        def _delegate_to_(self: 'Simulator', *args: Any, **kwargs: Any) -> Any:
            return f(self._net, *args, **kwargs)

        return cast("_F", _delegate_to_)

    # noinspection PyArgumentList
    add_type = _delegate_to(Net.add_type)
    # noinspection PyArgumentList
    add_place = _delegate_to(Net.add_place)
    # noinspection PyArgumentList
    add_immediate_transition = _delegate_to(Net.add_immediate_transition)
    # noinspection PyArgumentList
    add_timed_transition = _delegate_to(Net.add_timed_transition)
    # noinspection PyArgumentList
    add_constructor = _delegate_to(Net.add_constructor)
    # noinspection PyArgumentList
    add_transfer = _delegate_to(Net.add_transfer)
    # noinspection PyArgumentList
    add_destructor = _delegate_to(Net.add_destructor)
    # noinspection PyArgumentList
    add_test = _delegate_to(Net.add_test)
    # noinspection PyArgumentList
    add_inhibitor = _delegate_to(Net.add_inhibitor)

    def fire_repeatedly(self, count_of_firings: int):
        self._net.reset()
        self._token_counter.clear()
        self._sojourn_time.clear()
        self._auto_fire.reset()
        self._auto_fire.fire_repeatedly(count_of_firings)

    @property
    def bucket_boundaries_overall(self) -> Sequence[float]:
        return self._sojourn_time.bucket_boundaries_overall

    @bucket_boundaries_overall.setter
    def bucket_boundaries_overall(self, value: Sequence[float]):
        self._sojourn_time.bucket_boundaries_overall = value

    @property
    def bucket_boundaries_per_visit(self) -> Sequence[float]:
        return self._sojourn_time.bucket_boundaries_per_visit

    @bucket_boundaries_per_visit.setter
    def bucket_boundaries_per_visit(self, value: Sequence[float]):
        self._sojourn_time.bucket_boundaries_per_visit = value

    def token_count_histogram(self, place_name: str) -> Iterator[float]:
        """ Returns the empirical distribution of the number of tokens at a given place during the simulation.
        """
        return self._token_counter.histogram(place_name)

    def sojourn_time_overall_histogram(self, place_name: str) -> SojournTimePlugin.Histogram:
        """ Returns a histogram of the amount of time a token spends at a given place during its whole life."""
        return self._sojourn_time.overall_histogram(place_name)

    def sojourn_time_per_visit_histogram(self, place_name: str) -> SojournTimePlugin.Histogram:
        """ Returns a histogram of the amount of time a token spends at a given place during a visit."""
        return self._sojourn_time.per_visit_histogram(place_name)

# @dataclass(eq=False)
# class AbstractTokenObserver(Plugins.AbstractTokenObserver):
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

# AutoFirePlugin *-- "*" AbstractTransitionObserver
# AutoFirePlugin *-- "*" AbstractTokenObserver
# AutoFirePlugin *-- "*" AbstractPlaceObserver
# AutoFirePlugin ..|> Plugins.AbstractPlugin
# AbstractTransitionObserver ..|> Plugins.AbstractTransitionObserver
# AbstractTokenObserver ..|> Plugins.AbstractTokenObserver
# AbstractPlaceObserver ..|> Plugins.AbstractPlaceObserver
