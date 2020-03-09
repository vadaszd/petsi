from __future__ import annotations

from petsi import Plugins

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import collections

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, TYPE_CHECKING, Set, Dict, Deque, Callable, ValuesView


@dataclass
class Net:
    name: str
    _types: Dict[str, Type] = field(init=False, default_factory=dict)
    _places: Dict[str, Place] = field(init=False, default_factory=dict)
    _transitions: Dict[str, Transition] = field(init=False, default_factory=dict)
    _observers: Dict[str, Plugins.Observer] = field(init=False, default_factory=dict)
    _queuing_policies: Dict[str, Callable[[str, Type], Place]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self._queuing_policies["FIFO"] = FIFOPlace
        self._queuing_policies["LIFO"] = LIFOPlace

    @property
    def observers(self) -> ValuesView[Plugins.Observer]: return self._observers.values()

    def register_observer(self, observer: Plugins.Observer):
        if observer.name in self._observers:
            raise ValueError(f"An observer with name {observer.name} is already registered.")

        self._observers[observer.name] = observer

    # All arcs connected to a place must have the type of the place
    def add_type(self, type_name: str):
        if type_name in self._types:
            raise ValueError(f"Type '{type_name} is already defined in net "
                             f"'{self.name}'")
        typ = Type(type_name, self)
        self._types[type_name] = typ

    def add_place(self, name, typ: Type, queing_policy_name: str) -> Place:
        if name in self._places:
            raise ValueError(f"Place '{name}' already exists in net '{self.name}'")
        if typ.net is not self:
            raise ValueError(f"Type '{typ.name} does not belong to this net "
                             f"(was defined in '{typ.net.name}', not {self.name})")
        try:
            klass = self._queuing_policies[queing_policy_name]
        except KeyError:
            raise ValueError(f"Unknown queueing policy: '{queing_policy_name}'")
        else:
            place = self._places[name] = klass(name, typ)
            map(lambda o: o.observe_place(place), self._observers.values())
            return place

    # Arcs can be added only to empty input places!
    def add_immediate_transition(self, name: str, priority: int, weight: float) -> Transition: pass
    def add_timed_transition(self, name: str, firing_distribution: str) -> Transition: pass

    def add_constructor(self, name: str, transition_name: str, output_place_name: str) -> ConstructorArc: pass
    def add_destructor(self, name: str, transition_name: str, input_place_name: str) -> DestructorArc: pass
    def add_transfer(self, name: str, transition_name: str, input_place_name: str, output_place_name: str) -> TransferArc: pass
    def add_test(self, name: str, transition_name: str, place_name: str) -> TestArc: pass


@dataclass
class Type(ABC):
    _name: str
    _net: Net

    @property
    def name(self): return self._name

    @property
    def net(self): return self._net


@dataclass
class Token:
    _typ: Type
    _token_observers: Set[Plugins.TokenObserver] = field(default_factory=set, init=False)
    tags: Dict[str, Any] = field(init=False)

    def __post_init__(self):
        map(self._token_observers.add,
            map(lambda of: of.observe_token(self), self.typ.net.observers)
            )
        map(lambda to: to.report_construction(), self._token_observers)

    @property
    def typ(self): return self._typ

    def move_to(self, p: Place):
        map(lambda to: to.report_arrival_at(p), self._token_observers)

    def remove_from(self, place: Place):
        map(lambda to: to.report_departure_from(place), self._token_observers)

    def delete(self):
        map(lambda to: to.report_destruction(), self._token_observers)
        self._token_observers.clear()


# @dataclass
# class Tag:
#     key: str
#     value: Any


@dataclass
class Place(ABC):
    _name: str
    _typ:  Type
    _place_observers: Set[Plugins.PlaceObserver] = field(default_factory=set, init=False)
    _presence_observers: Set[PresenceObserver] = field(default_factory=set, init=False)

    @property
    def name(self): return self._name

    @property
    def typ(self): return self._typ

    @abstractmethod
    @property
    def is_empty(self) -> bool: pass

    def attach_place_observer(self, o: Plugins.PlaceObserver):
        self._place_observers.add(o)

    def attach_presence_observer(self, o: PresenceObserver):
        self._presence_observers.add(o)

    def pop(self) -> Token:
        token = self._pop()
        token.remove_from(self)
        map(lambda po: po.report_departure_of(token), self._place_observers)

        if self.is_empty:
            map(lambda po: po.report_no_token(), self._presence_observers)

        return token

    @abstractmethod
    def peek(self) -> Token: pass

    def push(self, token: Token):
        was_empty = self.is_empty

        # Move_to_place notifies observers. To show them a consistent picture,
        # we first update the place, only then call move_to_place
        self._push(token)
        token.move_to(self)
        map(lambda po: po.report_arrival_of(token), self._place_observers)

        if was_empty:
            map(lambda po: po.report_some_token(), self._presence_observers)

    @abstractmethod
    def _push(self, t: Token): pass

    @abstractmethod
    def _pop(self) -> Token: pass


class DequeBasedPlaceImplementation(Place, ABC):
    _tokens: Deque[Token] = field(default_factory=collections.deque, init=False)

    @property
    def is_empty(self):
        return len(self._tokens) == 0

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


@dataclass
class Transition:
    _name: str
    priority: int
    weight: float

    _deadline: float = field(init=False)
    _disabled_arc_count: int = field(init=False)
    _arcs: Dict[str, Arc] = field(init=False)
    _transition_observers: Set[Plugins.TransitionObserver] = field(init=False)

    @property
    def name(self): return self._name

    def attach_observer(self, o: Plugins.TransitionObserver): pass

    @property
    def is_enabled(self) -> bool:
        return self._disabled_arc_count == 0

    def fire(self):
        assert self.is_enabled, f"Transition '{self._name}' is disabled, it cannot be fired"
        map(lambda to: to.before_firing(), self._transition_observers)
        map(lambda arc: arc.flow(), self._arcs)
        map(lambda to: to.after_firing(), self._transition_observers)

    def increment_disabled_arc_count(self):
        old_disabled_arc_count = self._disabled_arc_count
        self._disabled_arc_count += 1

        if old_disabled_arc_count == 0:
            map(lambda to: to.got_disabled(), self._transition_observers)

    def decrement_disabled_arc_count(self):
        self._disabled_arc_count -= 1

        if self._disabled_arc_count == 0:
            map(lambda to: to.got_enabled(), self._transition_observers)


class Condition(ABC):
    @property
    @abstractmethod
    def is_true(self) -> bool: pass


@dataclass
class UpdateOp:
    key: str
    newValue: Any

    def apply(self, t: Token): pass


@dataclass
class Arc(ABC):
    _name: str
    _typ: Type
    _transition: Transition

    @property
    def name(self): return self._name

    @property
    def typ(self): return self._typ

    @abstractmethod
    @property
    def is_enabled(self) -> bool: pass

    @abstractmethod
    def flow(self):
        """ Move the token among places, according to the type of the arc"""


@dataclass
class TokenPlacer(Arc, ABC):
    _output_place: Place

    @property
    def is_enabled(self) -> bool: return True


@dataclass
class PresenceObserver(Arc, ABC):
    _input_place: Place
    _is_enabled: bool = field(init=False, default=False)

    @property
    def is_enabled(self) -> bool: return self._is_enabled

    def report_no_token(self):
        self._is_enabled = False
        self._transition.increment_disabled_arc_count()

    def report_some_token(self):
        self._is_enabled = True
        self._transition.decrement_disabled_arc_count()


class ConstructorArc(TokenPlacer):

    def flow(self):
        token = Token(self._typ)
        self._output_place.push(token)


class DestructorArc(PresenceObserver):

    def flow(self):
        token = self._input_place.pop()
        token.delete()


class TransferArc(PresenceObserver, TokenPlacer):
    def flow(self):
        token = self._input_place.pop()
        self._output_place.push(token)


class TestArc(PresenceObserver):
    def flow(self):
        pass


# Token *-- "*" Tag : tags
# TokenPlacer *--> "*" Updater : updates
# Updater *--> Condition
# Updater *--> UpdateOp


