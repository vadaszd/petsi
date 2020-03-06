from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import Plugins


@dataclass
class Net:
    name: str
    _types: Dict[str, Type] = field(init=False, default_factory=dict)
    _places: Dict[str, Place] = field(init=False, default_factory=dict)
    _transitions: Dict[str, Transition] = field(init=False, default_factory=dict)
    _observers: Dict[str, Observer] = field(init=False, default_factory=dict)

    # All arcs connected to a place must have the type of the place
    def add_type(self, type_name: str) -> Type: pass

    def add_place(self, name, typ: Type, klass: Callable[[str, Type], Place]) -> Place:
        if name in self._places:
            raise ValueError(f"Place '{name}' already exists in net '{self.name}'")
        place = self._places[name] = klass(name, typ)
        return place

    def add_immediate_transition(self, name: str, priority: int, weight: float) -> Transition: pass
    def add_timed_transition(self, name: str, firing_distribution: str) -> Transition: pass
    def add_constructor(self, name: str, transition_name: str, output_place_name: str) -> ConstructorArc: pass
    def add_destructor(self, name: str, transition_name: str, input_place_name: str) -> DestructorArc: pass
    def add_transfer(self, name: str, transition_name: str, input_place_name: str, output_place_name: str) -> TransferArc: pass
    def add_test(self, name: str, transition_name: str, place_name: str) -> TestArc: pass


@dataclass
class Type(ABC):
    _net: ref[Net] = field()


@dataclass
class Token:
    type: Type

    def attach_observer(self, o: Plugins.TokenObserver): pass
    def remove_observer(self, o: Plugins.TokenObserver): pass
    def move_to(self, p: Place): pass
    def remove_from(self, p: Place): pass


@dataclass
class Tag:
    key: str
    value: Any


@dataclass
class Place(ABC):
    name: str
    typ:  Type

    def attach_place_observer(self, o: Plugins.PlaceObserver): pass
    def attach_presence_observer(self, o: Plugins.PresenceObserver): pass

    @abstractmethod
    def push(self, t: Token): pass

    @abstractmethod
    def pop(self) -> Token: pass

    @abstractmethod
    def peek(self) -> Token: pass


class FIFOPlace(Place):
    def pop(self) -> Token:
        pass

    def peek(self) -> Token:
        pass

    def push(self, t: Token):
        pass

class LIFOPlace(Place):
    def pop(self) -> Token:
        pass

    def peek(self) -> Token:
        pass

    def push(self, t: Token):
        pass


@dataclass
class Transition:
    name: str
    priority: int
    weight: float
    deadline: float
    disabled_arc_count: int
    def attach_observer(self, o: Plugins.TransitionObserver): pass

    @property
    def is_enabled(self) -> bool:
        return self.disabled_arc_count == 0

    def fire(self): pass
    def increment_disabled_arc_count(self): pass
    def decrement_disabled_arc_count(self): pass


class Condition(ABC):
    @property
    @abstractmethod
    def is_true(self) -> bool: pass


@dataclass
class UpdateOp:
    key: str
    newValue: Any

    def apply(self, t: Token): pass


class Arc(ABC):
    name: str

    @property
    @abstractmethod
    def is_enabled(self) -> bool: pass

    @abstractmethod
    def flow(self):
        """ Move the token among places, according to the type of the arc"""


class TokenPlacer(ABC): pass

class PresenceObserver(ABC):
    @abstractmethod
    def report_no_token(self): pass

    @abstractmethod
    def report_some_token(self): pass


class ConstructorArc: pass
class DestructorArc: pass
class TransferArc: pass
class TestArc: pass

Place -l- "*" Token
Token *-- "*" Plugins.TokenObserver
Token *-- "*" Tag : tags
Place *-- "*" Plugins.PlaceObserver
TestArc .u.|> Arc
ConstructorArc  .u.|> Arc
DestructorArc  .u.|> Arc
TransferArc  .u.|> Arc
Transition *-- "*" Arc
Transition *-- "*" Plugins.TransitionObserver
PresenceObserver "*" <-- Place : input
TestArc .d.|> PresenceObserver
ConstructorArc .d.|> TokenPlacer
DestructorArc .d.|> PresenceObserver
TokenPlacer "*" --> Place : output
TransferArc  .d.|> TokenPlacer
TransferArc  .d.|> PresenceObserver
FIFO .u.|> Place
LIFO .u.|> Place
TokenPlacer *--> "*" Updater : updates
Updater *--> Condition
Updater *--> UpdateOp


