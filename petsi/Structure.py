from __future__ import annotations
import pyximport; pyximport.install(build_dir=".", inplace=True, build_in_temp=False, language_level=3)

import collections
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from more_itertools import flatten, consume

# mypy: mypy_path=..
from . import Plugins

if TYPE_CHECKING:
    from typing import Any, TYPE_CHECKING, Set, Dict, \
        Deque, Callable, ValuesView, Iterator

from .util import foreach


@dataclass(eq=False, repr=False)
class Net:
    name: str
    _types: Dict[str, TokenType] = field(init=False, default_factory=dict)
    _places: Dict[str, Place] = field(init=False, default_factory=dict)
    _transitions: Dict[str, Transition] = field(init=False, default_factory=dict)
    _observers: Dict[str, Plugins.AbstractPlugin] = field(init=False, default_factory=dict)
    _queuing_policies: Dict[str, Callable[[str, TokenType], Place]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._queuing_policies["FIFO"] = FIFOPlace
        self._queuing_policies["LIFO"] = LIFOPlace
        self._black_dot = self.add_type("black dot")

    @property
    def observers(self) -> ValuesView[Plugins.AbstractPlugin]: return self._observers.values()

    def register_plugin(self, of: Plugins.AbstractPlugin):
        if of.name in self._observers:
            raise ValueError(f"An observer with name '{of.name}' is already registered.")

        self._observers[of.name] = of
        foreach(lambda t: t.attach_observer(of), self._transitions.values())
        foreach(lambda p: p.attach_observer(of), self._places.values())
        foreach(lambda t: t.attach_observer(of),
                flatten(map(lambda p: p.tokens, self._places.values())))

    # All arcs connected to a place must have the type of the place
    def add_type(self, type_name: str) -> TokenType:
        if type_name in self._types:
            raise ValueError(f"Type '{type_name}' is already defined in net "
                             f"'{self.name}'")
        typ = TokenType(type_name, self)
        self._types[type_name] = typ
        return typ

    def add_place(self, name, type_name: str = "black dot", queueing_policy_name: str = "FIFO") -> Place:
        """ Add a place to the Petri-net with the given name, type and Qing policy.
        """
        if name in self._places:
            raise ValueError(f"Place '{name}' already exists in net '{self.name}'")
        if type_name not in self._types:
            raise ValueError(f"Type '{type_name}' does not exist in this net "
                             f"(it has to be added to the net first)")
        try:
            klass = self._queuing_policies[queueing_policy_name]
        except KeyError:
            raise ValueError(f"Unknown queueing policy: '{queueing_policy_name}'; "
                             f"valid values are { ', '.join(self._queuing_policies.keys()) }")
        else:
            place = self._places[name] = klass(name, self._types[type_name])
            foreach(lambda o: place.attach_observer(o),
                    self._observers.values())

            return place

    def _attach_transition_observers(self, t: Transition):
        foreach(lambda o: t.attach_observer(o),
                self._observers.values())

    def _validate_transition_name(self, name):
        if name in self._transitions:
            raise ValueError(f"A transition with name '{name}' already exists in net '{self.name}'.")

    # Arcs can be added only to empty input places!
    def add_immediate_transition(self, name: str, priority: int = 1, weight: float = 1.0) -> Transition:
        if not isinstance(priority, int) or priority < 1:
            raise ValueError(f"The priority of immediate transition '{name}' must be a positive integer")

        if not isinstance(weight, (float, int)) or weight <= 0:
            raise ValueError(f"The weight of immediate transition '{name}' must be a positive float")

        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, priority, weight, lambda: 0.0)
        self._attach_transition_observers(t)
        return t

    def add_timed_transition(self, name: str, distribution: Callable[[], float]) -> Transition:
        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, 0, 0.0, distribution)
        self._attach_transition_observers(t)
        return t

    def add_constructor(self, name: str, transition_name: str, output_place_name: str) -> ConstructorArc:
        return ConstructorArc(_name=name,
                              _transition=self._transitions[transition_name],
                              _output_place=self._places[output_place_name])

    def add_destructor(self, name: str, input_place_name: str, transition_name: str) -> DestructorArc:
        return DestructorArc(_name=name,
                             _transition=self._transitions[transition_name],
                             _input_place=self._places[input_place_name])

    def add_transfer(self, name: str, input_place_name: str, transition_name: str,
                     output_place_name: str) -> TransferArc:
        return TransferArc(_name=name,
                           _transition=self._transitions[transition_name],
                           _input_place=self._places[input_place_name],
                           _output_place=self._places[output_place_name])

    def add_test(self, name: str, place_name: str, transition_name: str, ) -> TestArc:
        return TestArc(_name=name,
                       _transition=self._transitions[transition_name],
                       _input_place=self._places[place_name])

    def add_inhibitor(self, name: str, place_name: str, transition_name: str, ) -> TestArc:
        return InhibitorArc(_name=name,
                            _transition=self._transitions[transition_name],
                            _input_place=self._places[place_name])

    def reset(self):
        """ Remove all tokens from the Petri net """
        for place in self._places.values():
            place.clear()


@dataclass(eq=False, repr=False)
class TokenType(ABC):
    _name: str
    _net: Net

    @property
    def name(self): return self._name

    @property
    def net(self): return self._net

    def __str__(self):
        return f"{self.__class__.__name__}('{self.name}')"


@dataclass(eq=False)
class Token:
    _typ: TokenType
    _token_observers: Set[Plugins.AbstractTokenObserver] = field(default_factory=set, init=False)
    tags: Dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        foreach(lambda of: self.attach_observer(of), self.typ.net.observers)
        # foreach(lambda to: to.report_construction(), self._token_observers)

    def attach_observer(self, plugin: Plugins.AbstractPlugin):
        observer = plugin.observe_token(self)

        if observer is not None:
            self._token_observers.add(observer)
            observer.report_construction()
            # observer.report_arrival_at(self.place)

    @property
    def typ(self): return self._typ

    def deposit_at(self, p: Place):
        foreach(lambda to: to.report_arrival_at(p), self._token_observers)

    def remove_from(self, place: Place):
        foreach(lambda to: to.report_departure_from(place), self._token_observers)

    def delete(self):
        foreach(lambda to: to.report_destruction(), self._token_observers)
        self._token_observers.clear()


# @dataclass
# class Tag:
#     key: str
#     value: Any

@dataclass(eq=False, repr=False)
class Transition:
    _name: str
    priority: int
    weight: float
    _distribution: Callable[[], float]

    _disabled_arc_count: int = field(default=0, init=False)
    _arcs: Dict[str, Arc] = field(default_factory=dict, init=False)
    _transition_observers: Set[Plugins.AbstractTransitionObserver] = field(default_factory=set, init=False)

    @property
    def name(self): return self._name

    @property
    def is_timed(self) -> bool:
        return self.priority == 0

    def get_duration(self):
        return self._distribution()

    def attach_observer(self, plugin: Plugins.AbstractPlugin):
        observer = plugin.observe_transition(self)

        if observer is not None:
            self._transition_observers.add(observer)

            if self.is_enabled:
                observer.got_enabled()
            else:
                # if not self.is_timed:
                    observer.got_disabled()

    def add_arc(self, arc: Arc):
        if arc.name in self._arcs:
            raise ValueError(f"An Arc with name '{arc.name}' already exists on Transition '{self.name}'")

        self._arcs[arc.name] = arc

    @property
    def is_enabled(self) -> bool:
        return self._disabled_arc_count == 0

    def fire(self):
        assert self.is_enabled, f"Transition '{self._name}' is disabled, it cannot be fired"
        foreach(lambda o: o.before_firing(), self._transition_observers)
        foreach(lambda arc: arc.flow(), self._arcs.values())
        foreach(lambda o: o.after_firing(), self._transition_observers)

    def increment_disabled_arc_count(self):
        old_disabled_arc_count = self._disabled_arc_count
        self._disabled_arc_count += 1

        if old_disabled_arc_count == 0:
            foreach(lambda to: to.got_disabled(), self._transition_observers)

    def decrement_disabled_arc_count(self):
        self._disabled_arc_count -= 1

        if self._disabled_arc_count == 0:
            foreach(lambda to: to.got_enabled(), self._transition_observers)


class Condition(ABC):
    @property
    @abstractmethod
    def is_true(self) -> bool: pass


@dataclass(frozen=True)
class UpdateOp:
    key: str
    newValue: Any

    def apply(self, t: Token): pass


@dataclass(eq=False, repr=False)
class Arc(ABC):
    _name: str
    _transition: Transition

    def __post_init__(self):
        self._transition.add_arc(self)

    @property
    def name(self): return self._name

    @property
    @abstractmethod
    def typ(self) -> TokenType: pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool: pass

    @abstractmethod
    def flow(self):
        """ Move the token among places, according to the type of the arc"""


class TokenConsumer(Arc, ABC):
    pass


@dataclass(eq=False)
class TokenPlacer(Arc, ABC):
    _output_place: Place

    @property
    def typ(self) -> TokenType: return self._output_place.typ

    @property
    def is_enabled(self) -> bool: return True


@dataclass(eq=False)
class PresenceObserver(Arc, ABC):
    """ An Arc-mixin providing the feature of enabling/disabling a transition.

        The arc is notified of the presence of a token at the input place.
        This information is forwarded to the transition so it can manage its enablement status.
    """
    _input_place: Place

    # Transitions track the number of disabled arcs. To match this,
    # we initialize _is_enabled = True.
    # When attaching ourselves to the input place, we get
    # a report_no_token or report_some_token callback so that
    # we can adjust the status and notify the transition, be there need.
    _is_enabled: bool = field(init=False, default=True)

    def __post_init__(self):
        # TODO: should the check happen before object construction?
        self._input_place.accept_arc(self, self._transition.is_timed)
        super(PresenceObserver, self).__post_init__()
        self._input_place.attach_presence_observer(self)

    @property
    def typ(self) -> TokenType: return self._input_place.typ

    @property
    def is_enabled(self) -> bool: return self._is_enabled

    def report_no_token(self):
        was_enabled = self._is_enabled
        self._is_enabled = False

        if was_enabled:
            self._transition.increment_disabled_arc_count()

    def report_some_token(self):
        was_enabled = self._is_enabled
        self._is_enabled = True

        if not was_enabled:
            self._transition.decrement_disabled_arc_count()


class ConstructorArc(TokenPlacer):

    def flow(self):
        token = Token(self._output_place.typ)
        self._output_place.push(token)


class DestructorArc(PresenceObserver, TokenConsumer):

    def flow(self):
        token = self._input_place.pop()
        token.delete()


@dataclass(eq=False)
class TransferArc(PresenceObserver, TokenPlacer, TokenConsumer):

    def __post_init__(self):
        # TODO: should the check happen before object construction?
        if self._input_place.typ is not self._output_place.typ:
            raise ValueError(f"Type mismatch on TransferArc('{self.name}'): "
                             f"type({self._input_place.name}) is '{self._input_place.typ.name}' whereas "
                             f"type({self._output_place.name}) is '{self._output_place.typ.name}'")
        super(TransferArc, self).__post_init__()

    def flow(self):
        token = self._input_place.pop()
        self._output_place.push(token)


class TestArc(PresenceObserver):
    def flow(self):
        pass


class InhibitorArc(TestArc):
    def report_some_token(self):
        super().report_no_token()

    def report_no_token(self):
        super().report_some_token()


@dataclass(eq=False)
class Place(ABC):
    _name: str
    _typ:  TokenType

    _Status = Enum("_Status", "UNDEFINED STABLE TRANSIENT ERROR")

    # ==== Invariants ======
    # The goal of the below invariants is to ensure that once a timed transition is enabled,
    # the only way to disable it is to fire it.
    # - A place can be stable or transient (or undefined until it becomes either stable or transient)
    # - A stable place can have at most one TokenConsumer arc and that arc must also be a
    # - All PresenceObserver arcs of timed transitions must connect to stable places

    # The next status to transit to, depending on the class of the input
    # arc and if the transition is timed
    _state_table = {
        _Status.UNDEFINED: {
            True:  [  # The order of the items is important!
                (TokenConsumer,     _Status.STABLE),    # May also be a PresenceObserver
                (PresenceObserver,  _Status.ERROR),     # Only those that are not TokenConsumers
            ],
            False: [
                (TokenConsumer,     _Status.TRANSIENT),  # May also be a PresenceObserver
                (PresenceObserver,  _Status.UNDEFINED),  # Only those that are not TokenConsumers
            ]
        },
        _Status.STABLE: {
            True: [
                (TokenConsumer,     _Status.ERROR),  # May also be a PresenceObserver
                (PresenceObserver,  _Status.ERROR),  # Only those that are not TokenConsumers
            ],
            False: [
                (TokenConsumer,     _Status.ERROR),  # May also be a PresenceObserver
                (PresenceObserver,  _Status.STABLE),  # Only those that are not TokenConsumers
            ]
        },
        _Status.TRANSIENT: {
            True: [
                (TokenConsumer,     _Status.ERROR),  # May also be a PresenceObserver
                (PresenceObserver,  _Status.ERROR),  # Only those that are not TokenConsumers
            ],
            False: [
                (TokenConsumer,     _Status.TRANSIENT),  # May also be a PresenceObserver
                (PresenceObserver,  _Status.TRANSIENT),  # Only those that are not TokenConsumers
            ]
        }
    }

    _status: _Status = field(default=_Status.UNDEFINED, init=False)

    _place_observers: Set[Plugins.AbstractPlaceObserver] = field(default_factory=set, init=False)
    _presence_observers: Set[PresenceObserver] = field(default_factory=set, init=False)

    def accept_arc(self, arc: Arc, is_timed: bool):
        arc_class = type(arc)
        for arc_type, status in self._state_table[self._status][is_timed]:
            if issubclass(arc_class, arc_type):
                if status == self._Status.ERROR:
                    break
                self._status = status
                return
        transition_kind = "a timed" if is_timed else "an immediate"
        raise ValueError(f"Connecting place '{self.name}' to {transition_kind} "
                         f"transition with a {arc_class.__name__} "
                         f"is not allowed: the place is in {self._status.name} "
                         f"status, which, for this kind of transitions, does not "
                         f"allow adding {arc_type.__name__} arcs.")

    @property
    def name(self): return self._name

    @property
    def typ(self): return self._typ

    @property
    @abstractmethod
    def is_empty(self) -> bool: pass

    @property
    @abstractmethod
    def tokens(self) -> Iterator[Token]: pass

    def clear(self):
        while not self.is_empty:
            self.pop()

    def attach_observer(self, plugin: Plugins.AbstractPlugin):
        observer = plugin.observe_place(self)

        if observer is not None:
            foreach(observer.report_arrival_of, self.tokens)
            self._place_observers.add(observer)

    def attach_presence_observer(self, o: PresenceObserver):
        self._presence_observers.add(o)

        if self.is_empty:
            o.report_no_token()
        else:
            o.report_some_token()

    def pop(self) -> Token:
        token: Token = self._pop()
        token.remove_from(self)
        foreach(lambda po: po.report_departure_of(token), self._place_observers)

        if self.is_empty:
            foreach(lambda po: po.report_no_token(), self._presence_observers)

        return token

    @abstractmethod
    def peek(self) -> Token: pass

    def push(self, token: Token):
        was_empty = self.is_empty

        # Move_to_place notifies observers. To show them a consistent picture,
        # we first update the place, only then call move_to_place
        self._push(token)
        token.deposit_at(self)
        foreach(lambda po: po.report_arrival_of(token), self._place_observers)

        if was_empty:
            foreach(lambda po: po.report_some_token(), self._presence_observers)

    @abstractmethod
    def _push(self, t: Token): pass

    @abstractmethod
    def _pop(self) -> Token: pass


@dataclass(eq=False)
class DequeBasedPlaceImplementation(Place, ABC):
    _tokens: Deque[Token] = field(default_factory=collections.deque, init=False)

    @property
    def is_empty(self):
        return len(self._tokens) == 0

    @property
    def tokens(self) -> Iterator[Token]:
        return iter(self._tokens)

    def _pop(self) -> Token:
        return self._tokens.popleft()

    def peek(self) -> Token:
        return self._tokens[0]


class FIFOPlace(DequeBasedPlaceImplementation):
    def _push(self, t: Token):
        self._tokens.append(t)  # Appends to the right


class LIFOPlace(DequeBasedPlaceImplementation):
    def _push(self, t: Token):
        self._tokens.appendleft(t)

