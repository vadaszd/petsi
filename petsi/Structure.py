from __future__ import annotations

from . import Plugins

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import collections
from itertools import chain

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, TYPE_CHECKING, Set, Dict, \
        Deque, Callable, ValuesView, Iterator


@dataclass(eq=False, repr=False)
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
        map(lambda t: observer.observe_transition(t), self._transitions.values())
        map(lambda p: observer.observe_place(p), self._places.values())
        map(lambda t: observer.observe_token(t),
            chain.from_iterable(map(lambda p: p.tokens, self._places.values())))

    # All arcs connected to a place must have the type of the place
    def add_type(self, type_name: str):
        if type_name in self._types:
            raise ValueError(f"Type '{type_name}' is already defined in net "
                             f"'{self.name}'")
        typ = Type(type_name, self)
        self._types[type_name] = typ

    def add_place(self, name, type_name: str, queueing_policy_name: str) -> Place:
        if name in self._places:
            raise ValueError(f"Place '{name}' already exists in net '{self.name}'")
        if type_name not in self._types:
            raise ValueError(f"Type '{type_name}' does not exist in this net "
                             f"(it has to be added to the net first)")
        try:
            klass = self._queuing_policies[queueing_policy_name]
        except KeyError:
            raise ValueError(f"Unknown queueing policy: '{queueing_policy_name}'")
        else:
            place = self._places[name] = klass(name, self._types[type_name])
            map(lambda o: place.attach_place_observer(o.observe_place(place)),
                self._observers.values())

            return place

    def _validate_transition_name(self, name):
        if name in self._transitions:
            raise ValueError(f"A transition with name '{name}' already exists in net '{self.name}'.")

    # Arcs can be added only to empty input places!
    def add_immediate_transition(self, name: str, priority: int, weight: float) -> Transition:
        if not isinstance(priority, int) or priority < 1:
            raise ValueError(f"The priority of immediate transition '{name}' must be a positive integer")

        if not isinstance(weight, float) or weight <= 0:
            raise ValueError(f"The weight of immediate transition '{name}' must be a positive float")

        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, priority, weight, lambda: 0.0)
        return t

    def add_timed_transition(self, name: str, distribution: Callable[[], float]) -> Transition:
        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, 0, 0.0, distribution)
        return t

    def add_constructor(self, name: str, transition_name: str, output_place_name: str) -> ConstructorArc:
        return ConstructorArc(name, self._transitions[transition_name], self._places[output_place_name])

    def add_destructor(self, name: str, transition_name: str, input_place_name: str) -> DestructorArc:
        return DestructorArc(name, self._transitions[transition_name], self._places[input_place_name])

    def add_transfer(self, name: str, transition_name: str,
                     input_place_name: str, output_place_name: str) -> TransferArc:
        return TransferArc(name, self._transitions[transition_name],
                           self._places[input_place_name], self._places[output_place_name])

    def add_test(self, name: str, transition_name: str, place_name: str) -> TestArc:
        return TestArc(name, self._transitions[transition_name], self._places[place_name])


@dataclass(eq=False, repr=False)
class Type(ABC):
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
    _typ: Type
    _token_observers: Set[Plugins.TokenObserver] = field(default_factory=set, init=False)
    tags: Dict[str, Any] = field(default_factory=dict, init=False)

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


@dataclass(eq=False)
class Place(ABC):
    _name: str
    _typ:  Type
    _place_observers: Set[Plugins.PlaceObserver] = field(default_factory=set, init=False)
    _presence_observers: Set[PresenceObserver] = field(default_factory=set, init=False)

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


@dataclass(eq=False, repr=False)
class Transition:
    _name: str
    priority: int
    weight: float
    _distribution: Callable[[], float]

    _deadline: float = field(default=0, init=False)
    _disabled_arc_count: int = field(default=0, init=False)
    _arcs: Dict[str, Arc] = field(default_factory=dict, init=False)
    _transition_observers: Set[Plugins.TransitionObserver] = field(default_factory=set, init=False)

    @property
    def name(self): return self._name

    def attach_observer(self, o: Plugins.TransitionObserver): pass

    def add_arc(self, arc: Arc):
        if arc.name in self._arcs:
            raise ValueError(f"An Arc with name '{arc.name}' already exists on Transition '{self.name}'")

        self._arcs[arc.name] = arc

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
    def typ(self) -> Type: pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool: pass

    @abstractmethod
    def flow(self):
        """ Move the token among places, according to the type of the arc"""


@dataclass(eq=False)
class TokenPlacer(Arc, ABC):
    _output_place: Place

    @property
    def typ(self) -> Type: return self._output_place.typ

    @property
    def is_enabled(self) -> bool: return True


@dataclass(eq=False)
class PresenceObserver(Arc, ABC):
    _input_place: Place
    _is_enabled: bool = field(init=False, default=False)

    def __post_init__(self):
        self._input_place.attach_presence_observer(self)

    @property
    def typ(self) -> Type: return self._input_place.typ

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


@dataclass(eq=False)
class TransferArc(PresenceObserver, TokenPlacer):

    def __post_init__(self):
        if self._input_place.typ is not self._output_place.typ:
            raise ValueError(f"Type mismatch on TransferArc('{self.name}'): "
                             f"type({self._input_place.name}) is {self._input_place.typ} whereas "
                             f"type({self._output_place.name}) is {self._output_place.typ})")

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


