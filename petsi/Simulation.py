from array import array
from dataclasses import dataclass, field
from functools import wraps
from itertools import count
from typing import TYPE_CHECKING, Optional, Dict, Callable, Iterator, TypeVar, Any, cast, \
    Tuple, FrozenSet, Generic, Type

from .NetViz import Visualizer
from .Plugins import AbstractPlugin, APlaceObserver, ATokenObserver, ATransitionObserver, \
    NoopTokenObserver, NoopTransitionObserver, NoopPlaceObserver
from .Structure import APetsiVisitor, Net, Place, Token, Transition
from .autofire import AutoFirePlugin
from .fire_control import Clock
from .meters import SojournTimePluginTokenObserver, TokenCounterPluginPlaceObserver, \
    TransitionIntervalPluginTransitionObserver, FiringCollector, GenericCollector, SojournTimeCollector, \
    TokenCounterCollector

if TYPE_CHECKING:
    from graphviz import Digraph

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


ACollector = TypeVar("ACollector", bound=GenericCollector)


@dataclass(eq=False)
class _MeterPlugin(Generic[ACollector, APlaceObserver, ATransitionObserver, ATokenObserver],  #
                   AbstractPlugin[APlaceObserver, ATransitionObserver, ATokenObserver],
                   ):
    _places: Optional[FrozenSet[int]]           # Observe these places only
    _token_types: Optional[FrozenSet[int]]      # Observe these token types only
    _transitions: Optional[FrozenSet[int]]      # Observe these transitions only
    _clock: Clock
    _collector: ACollector = field(init=False)

    def get_observations(self) -> Dict[str, array]:
        return self._collector.get_observations()


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
        self._collector = TokenCounterCollector()

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
        self._collector = SojournTimeCollector()

    def token_observer_factory(self, t: "Token") -> Optional[SojournTimePluginTokenObserver]:
        return SojournTimePluginTokenObserver(self, t, self._places, self._clock,
                                              self._collector, next(self.token_id)) \
            if self._token_types is None or t.typ.ordinal in self._token_types else None


@dataclass(eq=False)
class TransitionIntervalPlugin(
        _MeterPlugin[FiringCollector,
                     NoopPlaceObserver, TransitionIntervalPluginTransitionObserver, NoopTokenObserver]):

    def __post_init__(self):
        self._collector = FiringCollector()

    def transition_observer_factory(self, t: "Transition") -> \
            Optional[TransitionIntervalPluginTransitionObserver]:

        return TransitionIntervalPluginTransitionObserver(self, t, self._clock, self._collector) \
            if self._transitions is None or t.ordinal in self._transitions else None


class Simulator:
    _net: Net
    _auto_fire: AutoFirePlugin

    _meter_plugins: Dict[str, Type[_MeterPlugin]] = \
        dict(token_visits=SojournTimePlugin,
             place_population=TokenCounterPlugin,
             transition_firing=TransitionIntervalPlugin,
             )

    def __init__(self, net_name: str = "net",):
        """ Create a Simulator object

        :param net_name:    The name of the Petri-net
        """
        self._net = Net(net_name)
        self._auto_fire = AutoFirePlugin("auto-fire plugin")
        self._net.register_plugin(self._auto_fire)

    def observe(self, stream: str,
                places: Optional[FrozenSet[str]] = None,
                transitions: Optional[FrozenSet[str]] = None,
                token_types: Optional[FrozenSet[str]] = None,
                ) -> Callable[[], Dict[str, array]]:
        """ Create an observation stream

        :param stream: The type of the stream. Currently the following types are supported:
                        - `token_visits`
                        - `place_population`
                        - `transition_firing`
                       Only one stream of each type can be created.

        :param places:  The places to observe. Observes all places when set to `None`.
                        This parameter is ignored for the `transition_firing` stream.
        :param transitions: The transitions to observe. Observes all transitions when set to `None`.
                        This parameter is ignored for the `token_visits` and `place_population` streams.
        :param token_types: The type of tokens to observe. Observes all types when set to `None`.
                        This parameter is ignored for the `transition_firing` and `place_population` streams.
        :return:        A callable returning the observations
        """
        plugin_type = self._meter_plugins[stream]

        _places = None if places is None \
            else map(lambda n: self._net.place(n).ordinal, places)
        _token_types = None if token_types is None \
            else map(lambda n: self._net.token_type(n).ordinal, token_types)
        _transitions = None if transitions is None \
            else map(lambda n: self._net.transition(n).ordinal, transitions)
        name = stream
        _clock = self._auto_fire.clock

        # Create the plugin
        plugin = plugin_type(name, _places, _token_types, _transitions, _clock)
        self._net.register_plugin(plugin)

        return plugin.get_observations

    @property
    def net(self) -> Net: return self._net

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
