from bisect import bisect
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps, cached_property
from itertools import repeat
from typing import TYPE_CHECKING, Optional, List, Dict, Callable, Iterator, TypeVar, Any, cast, \
    Sequence, Tuple

from graphviz import Digraph

from .fire_control import Clock

from . import Plugins
from .NetViz import Visualizer
from .Plugins import NoopTokenObserver, NoopTransitionObserver, NoopPlaceObserver
from .Structure import foreach, Net, APetsiVisitor
from .fire_control import FireControl, SojournTimePluginTokenObserver, TokenCounterPluginPlaceObserver

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

    _fire_control: FireControl = field(default_factory=FireControl, init=False)

    @cached_property
    def clock(self) -> Clock:
        return self._fire_control.get_clock()

    def reset(self): self._fire_control.reset()

    def fire_until(self, end_time: float):
        clock: Clock = self.clock
        self._fire_control.start()

        while clock.read() < end_time:
            self._fire_control.fire_next()

    def fire_repeatedly(self, count_of_firings: int = 0):
        self._fire_control.start()

        foreach(lambda _: self._fire_control.fire_next(),
                repeat(None) if count_of_firings == 0 else repeat(None, count_of_firings))

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional["AutoFirePlugin.TransitionObserver"]:
        return self.TransitionObserver(self, t, self._fire_control)

    @dataclass(eq=False)
    class TransitionObserver(Plugins.NoopTransitionObserver["AutoFirePlugin"]):

        _fire_control: "FireControl"
        _deadline: float = field(default=0.0, init=False)

        def got_enabled(self, ):
            self._fire_control.enable_transition(self._transition)

        def got_disabled(self, ):
            self._fire_control.disable_transition(self._transition)


@dataclass(eq=False)
class Histogram:
    _bucket_boundaries: Sequence[float]
    _buckets: List[int] = field(init=False)
    _bucket_sizes: List[int] = field(init=False)
    _min_value: float = field(default=0.0, init=False)
    _max_value: float = field(default=0.0, init=False)
    _sum_value: float = field(default=0.0, init=False)

    def __post_init__(self):
        self._buckets = list(repeat(0, len(self._bucket_boundaries) + 1))
        self._bucket_sizes = [(upper - lower) for (upper, lower) in zip(self._bucket_boundaries[1:],
                                                                        self._bucket_boundaries)]

    def __iter__(self) -> Iterator[float]:
        """ Iterate over the buckets of the histogram, yielding the number of items in each bucket"""
        num_values_total = float(self.num_values)
        for bucket_value in self._buckets:
            yield bucket_value / num_values_total

    @property
    def density(self):
        for bucket_value, size in zip(self._buckets[1:], self._bucket_sizes):
            yield bucket_value / size

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
        return self._sum_value / self.num_values if self.num_values != 0 else 0

    @cached_property
    def num_values(self):
        """ :returns The number of items addedd to the histogram.

            Caveat!!! Only call this function after adding all items to the histogram,
            as the return value is cached and not recalculated for subsequent invocations.
         """
        return sum(self._buckets)


@dataclass(eq=False)
class TokenCounterPlugin(
        Plugins.AbstractPlugin["TokenCounterPluginPlaceObserver", NoopTransitionObserver, NoopTokenObserver]):

    """ A PetSi plugin providing by-place token-count stats

        The plugin collects the empirical distribution of the
        time-weighted token counts at all places of the observed Petri net,
        i.e. in what percentage of time the token count is i at place j.

        :arg _clock   A callable returning the current simulation time
    """

    # A function returning the current time
    _clock: Clock

    def histogram(self, place_name: str) -> Iterator[float]:
        return self._place_observers[place_name].histogram

    def place_observer_factory(self, p: "Structure.Place") -> Optional["Plugins.APlaceObserver"]:
        return TokenCounterPluginPlaceObserver(self, p, self._clock)


@dataclass(eq=False)
class SojournTimePlugin(
        Plugins.AbstractPlugin[NoopPlaceObserver, NoopTransitionObserver, "SojournTimePluginTokenObserver"]):
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

    _clock: Clock

    bucket_boundaries_per_visit: Sequence[float] = field(default=(), init=False)
    bucket_boundaries_overall: Sequence[float] = field(default=(), init=False)

    _per_visit_histograms: Dict[str, Histogram] = field(init=False)

    # A s.t. histogram for each place
    _overall_histograms: Dict["str", Histogram] = field(init=False)

    def reset(self):
        """ Clear the state of the plugin.

        Removes all token observers and the data collected during the previous simulation.
        """
        self._per_visit_histograms.clear()
        self._overall_histograms.clear()
        super().reset()

    def per_visit_histogram(self, place_name) -> Histogram:
        return self._per_visit_histograms[place_name]

    def overall_histogram(self, place_name) -> Histogram:
        return self._overall_histograms[place_name]

    def __post_init__(self):
        self._per_visit_histograms = defaultdict(self._new_per_visit_histogram)
        self._overall_histograms = defaultdict(self._new_overall_histogram)

    def _new_per_visit_histogram(self):
        return Histogram(self.bucket_boundaries_per_visit)

    def _new_overall_histogram(self):
        return Histogram(self.bucket_boundaries_overall)

    def token_observer_factory(self, t: "Structure.Token") -> Optional["Plugins.ATokenObserver"]:
        return SojournTimePluginTokenObserver(self, t, self._clock)


@dataclass(eq=False)
class TransitionIntervalPlugin(
        Plugins.AbstractPlugin[NoopPlaceObserver, "TransitionIntervalPlugin.TransitionObserver", NoopTokenObserver]):

    clock: Clock
    bucket_boundaries: Sequence[float] = field(default=(), init=False)

    def transition_observer_factory(self, t: "Structure.Transition") -> \
            Optional["TransitionIntervalPlugin.TransitionObserver"]:
        return self.TransitionObserver(self, t)

    def firing_interval_histogram(self, transition_name: str) -> Histogram:
        return self._transition_observers[transition_name].histogram

    @dataclass(eq=False)
    class TransitionObserver(Plugins.NoopTransitionObserver["TransitionIntervalPlugin"]):

        previous_firing_time: float = field(init=False)
        histogram: Histogram = field(init=False)

        def __post_init__(self):
            self.previous_firing_time = self._plugin.clock.read()
            self.histogram = Histogram(self._plugin.bucket_boundaries)

        def after_firing(self, ):
            now = self._plugin.clock.read()
            self.histogram.add(now - self.previous_firing_time)
            self.previous_firing_time = now

        def reset(self):
            self.__post_init__()


class Simulator:
    def __init__(self, net_name: str = "net"):
        self._net = Net(net_name)
        self._auto_fire = AutoFirePlugin("auto-fire plugin")
        self._net.register_plugin(self._auto_fire)
        self._token_counter = TokenCounterPlugin("token counter plugin", self._auto_fire.clock)
        self._net.register_plugin(self._token_counter)
        self._sojourn_time = SojournTimePlugin("sojourn time plugin", self._auto_fire.clock,)
        self._net.register_plugin(self._sojourn_time)
        self._transition_interval = TransitionIntervalPlugin("transition interval plugin", self._auto_fire.clock, )
        self._net.register_plugin(self._transition_interval)

    @property
    def net(self) -> "Structure.Net": return self._net

    def visit_net(self, visualizer: APetsiVisitor) -> APetsiVisitor:
        return self._net.accept(visualizer)

    def show(self, figsize: Optional[Tuple[float, float]] = None) -> "Digraph":
        return self.visit_net(Visualizer(figsize)).dot

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
        self._auto_fire.fire_repeatedly(count_of_firings)

    @property
    def st_bucket_boundaries_overall(self) -> Sequence[float]:
        return self._sojourn_time.bucket_boundaries_overall

    @st_bucket_boundaries_overall.setter
    def st_bucket_boundaries_overall(self, value: Sequence[float]):
        self._sojourn_time.bucket_boundaries_overall = value

    @property
    def st_bucket_boundaries_per_visit(self) -> Sequence[float]:
        return self._sojourn_time.bucket_boundaries_per_visit

    @st_bucket_boundaries_per_visit.setter
    def st_bucket_boundaries_per_visit(self, value: Sequence[float]):
        self._sojourn_time.bucket_boundaries_per_visit = value

    @property
    def transition_interval_bucket_boundaries(self) -> Sequence[float]:
        return self._transition_interval.bucket_boundaries

    @transition_interval_bucket_boundaries.setter
    def transition_interval_bucket_boundaries(self, value: Sequence[float]):
        self._transition_interval.bucket_boundaries = value

    def token_count_histogram(self, place_name: str) -> Iterator[float]:
        """ Returns the empirical distribution of the number of tokens at a given place during the simulation.
        """
        return self._token_counter.histogram(place_name)

    def sojourn_time_overall_histogram(self, place_name: str) -> Histogram:
        """ Returns a histogram of the amount of time a token spends at a given place during its whole life."""
        return self._sojourn_time.overall_histogram(place_name)

    def sojourn_time_per_visit_histogram(self, place_name: str) -> Histogram:
        """ Returns a histogram of the amount of time a token spends at a given place during a visit."""
        return self._sojourn_time.per_visit_histogram(place_name)

    def transition_interval_histogram(self, transition_name: str) -> Histogram:
        """ Returns a histogram of the amount of time a token spends at a given place during a visit."""
        return self._transition_interval.firing_interval_histogram(transition_name)
