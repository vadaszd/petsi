""" A high level API for creating a performance simulator.
"""

import os
import re
from array import array, typecodes
from collections import defaultdict
from functools import wraps, reduce
from glob import glob
from typing import TYPE_CHECKING, Optional, Dict, Callable, TypeVar, Any, cast, \
    Tuple, FrozenSet, Iterable, List

from .plugins.meters import MeterPlugin
from .plugins.transitioninterval import TransitionIntervalPlugin
from .plugins.sojourntime import SojournTimePlugin
from .plugins.tokencounter import TokenCounterPlugin

from .netviz import Visualizer
from ._structure import Net
from .plugins.autofire import AutoFirePlugin
from .plugins.autofire import Clock

if TYPE_CHECKING:
    from graphviz import Digraph


class Simulator:
    """ The entry point for creating a performance simulator.

    The elements of the Petri net must be created in reverse order of reference, i.e.

        #. Token types
        #. Places and transitions
        #. Arcs
    """
    _net: Net
    _auto_fire: AutoFirePlugin
    _meters: Dict[str, MeterPlugin]
    _need_more_observations: List[Callable[[], bool]]

    # Type[_MeterPlugin] Callable[[str, ], _MeterPlugin]
    _meter_plugins: Dict[str, Callable[[str, int,
                                        Optional[FrozenSet[int]],
                                        Optional[FrozenSet[int]],
                                        Optional[FrozenSet[int]],
                                        Clock],
                                       MeterPlugin]] = \
        dict(token_visits=SojournTimePlugin,
             place_population=TokenCounterPlugin,
             transition_firing=TransitionIntervalPlugin,
             )

    def __init__(self, net_name: str = "net",):
        """ Create a Simulator object.

        :param net_name:    The name of the Petri net
        """
        self._net = Net(net_name)
        self._auto_fire = AutoFirePlugin("auto-fire plugin")
        self._net.register_plugin(self._auto_fire)
        self._meters = dict()
        self._need_more_observations = list()

    def observe(self,
                places: Optional[Iterable[str]] = None,
                transitions: Optional[Iterable[str]] = None,
                token_types: Optional[Iterable[str]] = None,
                **required_observations: int,
                ) -> Tuple[Callable[[], Dict[str, array]], ...]:
        """ Create one or more observation streams.

        This method may be called several times to specify various observation critera like the places, transitions and
        token types to observe. The criteria provided in each call apply to the stream types specified in
        ``required_observations``. There must be no overlap between the stream types specified in subsequent calls
        to ``observe()``.

        :param required_observations:
            Keyword arguments specifying the types of the streams to observe.
                Currently the following types are supported:
                - ``token_visits``
                - ``place_population``
                - ``transition_firing``

            Only one stream of each type can be created.
            The value assigned is the number of observations to produce in each stream.

        :param places:  The places to observe. Observes all places when set to ``None``.
                        This parameter is ignored for the ``transition_firing`` stream.
        :param transitions: The transitions to observe. Observes all transitions when set to ``None``.
                        This parameter is ignored for the ``token_visits`` and ``place_population`` streams.
        :param token_types: The type of tokens to observe. Observes all types when set to ``None``.
                        This parameter is ignored for the ``transition_firing`` and ``place_population`` streams.
        :return:        A tuple of callables returning the observations as a dictionary of Python arrays.
                        The order of the callables matches the order of the stream types in ``required_observations``.
        :raise KeyError: ``required_observations`` got an unexpected stream type.
        :raise ValueError: There is an overlap in ``required_observations`` of an earlier call to ``observer()``.
        """
        _places = None if places is None \
            else frozenset(self._net.place(p).ordinal for p in places)
        _token_types = None if token_types is None \
            else frozenset(self._net.token_type(t).ordinal for t in token_types)
        _transitions = None if transitions is None \
            else frozenset(self._net.transition(t).ordinal for t in transitions)
        _clock = self._auto_fire.clock

        get_observations: List[Callable[[], Dict[str, array]]] = list()
        for stream, n in required_observations.items():
            plugin_type = self._meter_plugins[stream]

            # Create the plugin
            plugin: MeterPlugin = plugin_type(stream, n, _places, _token_types, _transitions, _clock)
            self._net.register_plugin(plugin)
            self._meters[stream] = plugin
            self._need_more_observations.append(plugin.get_need_more_observations())
            get_observations.append(plugin.get_observations)

        return tuple(get_observations)

    def required_observations(self, **required_observations: int):
        """ Specify the number of observations to collect during one call to :func:`simulate`.

        This method can be used to override the values provided in :func:`observe`.

        :param required_observations:
            Keyword arguments specifying the number of observations in each stream. The allowed keys are:
                - ``token_visits``
                - ``place_population``
                - ``transition_firing``

        :raise KeyError: An unknown stream type is provided as keyword argument
        """
        for stream, n in required_observations.items():
            self._meters[stream].required_observations = n

    def need_more_observations(self) -> bool:
        return any(map(lambda c: c(), self._need_more_observations))

    def fire_repeatedly(self, count_of_firings: int):
        """ Fire ``count_of_firings`` transitions.

        This method ignores the limits provided in :func:`observe()` or :func:`required_observations()`.

        The actual number of firings performed may be less if the enabled transitions are exhausted.
        """
        self._net.reset()
        self._auto_fire.fire_repeatedly(count_of_firings)

    def simulate(self):
        """ Run a simulation using the Petri net.

        The net will keep firing transitions until all transitions get disabled or the required number of
        observations have been collected (see the ``required_observations`` parameter in :func:`observe()`
        and :func:`required_observations()`).
        """
        self._net.reset()
        self._auto_fire.fire_while(self.need_more_observations)

    @property
    def net(self) -> Net:
        """ The underlying :class:`~petsi._structure.Net` object representing the Petri net.
        """
        return self._net

    def show(self, figsize: Optional[Tuple[float, float]] = None) -> "Digraph":
        """ Render a `graphviz <https://www.graphviz.org/>`_ graph representing the Petri net.

        :param figsize: The size (in inches) of the figure to create.
        :return: A :class:`graphviz.Digraph` object representing the graph.

        .. note:: IPython will automatically display the graph as a picture when this object is the return value
                  of the last statement in a code cell.

                  When this is not the case, the object can be programmatically displayed as::

                      from IPython.display import display
                      display(simulator.show())
        """
        return self.visit_net(Visualizer(figsize)).dot

    _FuncType = Callable[..., Any]
    _F = TypeVar('_F', bound=_FuncType)

    # noinspection Mypy,PyMethodParameters
    def _delegate_to(f: _F) -> _F:
        @wraps(f)
        def _delegate_to_(self: 'Simulator', *args: Any, **kwargs: Any) -> Any:
            return f(self._net, *args, **kwargs)

        return cast("_F", _delegate_to_)

    # def visit_net(self, visualizer: APetsiVisitor) -> APetsiVisitor:
    #     return self._net.accept(visualizer)

    # noinspection PyArgumentList
    visit_net = _delegate_to(Net.accept)
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


def save_array(a: array, file_name_prefix: str, ):
    filename = f"{file_name_prefix}.array_{a.typecode}"
    a.tofile(open(filename, "wb"))


def save_observations(observations: Dict[str, array], file_name_prefix: str, ):
    for metric_name, a in observations.items():
        save_array(a, f"{file_name_prefix}_{metric_name}")


def load_array(file_name_prefix: str, a: Optional[array] = None, typecode: Optional[str] = None) -> array:
    """ Load an array from a file.

    :param file_name_prefix:  The path to the file. If the ".array_{typecode}" extension is missing, it will be
                                    appended.
    :param a:                 Load into this array. If None, a new array will be created.
    :param typecode:          The type code of the array. Required only if the file_name_prefix matches multiple
                                files on the disk; in such cases it is used for disambiguation.
                                If not None, must match the type code embedded in the name of the file found on disk.
    :return:                  The loaded array.
    """
    if a is None:
        if typecode is None:
            pattern = f"{file_name_prefix}.array_*"
            file_names: List[str] = glob(pattern)

            if len(file_names) == 0:
                file_names = glob(file_name_prefix)

            if len(file_names) == 0:
                raise ValueError(f"No file to load the array from. Seeking for {pattern}")

            if len(file_names) > 1:
                raise ValueError(f"Cannot choose a file to load the array from. "
                                 f"Please specify a type code. Candidates: {', '.join(file_names)}")

            file_name = file_names[0]
            m = re.match(".+\\.array_(?P<typecode>.+)", file_name)

            if m is None:
                raise ValueError(f"{file_name} contains no type code.")

            typecode = m.group('typecode')

            if len(typecode) > 1 or typecode not in typecodes:
                raise ValueError(f"Cannot load {file_name}: unknown type code '{typecode}'")

        a = array(typecode)
    else:
        if typecode is None:
            typecode = a.typecode
        else:
            if typecode != a.typecode:
                raise ValueError(
                    f"np_array.typecode={a.typecode} but in the argument typecode={typecode} was provided")

    filename = f"{file_name_prefix}.array_{typecode}"
    file_size = os.stat(filename).st_size

    if file_size % a.itemsize:
        raise ValueError(f"The size of {filename} is not a multiple of itemsize '{a.itemsize}'")

    a.fromfile(open(filename, "rb"), int(file_size / a.itemsize))

    return a


def load_observations(file_name_prefix: str, ) -> Dict[str, array]:
    observations: Dict[str, array] = dict()

    for file_name in glob(f"{file_name_prefix}_*.array_*"):
        m = re.match(".*_(?P<metric_name>[^_]+)\\.array_.", file_name)

        if m is None:
            raise ValueError(f"{file_name} contains no metric name")

        metric_name = m.group('metric_name')
        observations[metric_name] = load_array(file_name)

    return observations


def flatten_observations(observations: Iterable[Dict[str, array]]) -> Dict[str, array]:
    transposed = defaultdict(list)

    for metric_dict in observations:
        for metric_name, value_array in metric_dict.items():
            transposed[metric_name].append(value_array)

    def concatenate(a: array, b: array) -> array:
        a.extend(b)
        return a

    flat_observations: Dict[str, array] = dict()
    for metric_name, value_array_list in transposed.items():
        flat_observations[metric_name] = reduce(concatenate, value_array_list)

    return flat_observations
