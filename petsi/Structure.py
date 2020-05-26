# cython: language_level=3
# cython: profile=False

# You may compile this file as:
#    cythonize --3str -a -f -i petsi/Structure.py

import collections
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Union, TypeVar

from more_itertools import flatten
import cython


# mypy: mypy_path=..
from . import Plugins

if TYPE_CHECKING:
    from typing import Any, TYPE_CHECKING, Set, Dict, \
        Deque, Callable, ValuesView, Iterator

from .util import foreach


APetsiVisitor = TypeVar('APetsiVisitor', bound="PetsiVisitor")


class Net:
    name: str
    _types: "Dict[str, TokenType]"
    _places: "Dict[str, Place]"
    _transitions: "Dict[str, Transition]"
    _observers: "Dict[str, Plugins.AbstractPlugin]"
    _queuing_policies: "Dict[str, Callable[[str, int, TokenType], Place]]"

    def __init__(self, name: str):
        self.name = name
        self._types = dict()
        self._places = dict()
        self._transitions = dict()
        self._observers = dict()
        self._queuing_policies = dict(FIFO=FIFOPlace, LIFO=LIFOPlace)
        self._black_dot = self.add_type("black dot")

    def accept(self, visitor: APetsiVisitor) -> APetsiVisitor:
        visitor.visit(self)

        for place in self._places.values():
            place.accept(visitor)

        for transition in self._transitions.values():
            transition.accept(visitor)

        return visitor

    @property
    def observers(self) -> "ValuesView[Plugins.AbstractPlugin]":
        return self._observers.values()

    def register_plugin(self, of: "Plugins.AbstractPlugin"):
        if of.name in self._observers:
            raise ValueError(f"An observer with name '{of.name}' is already registered.")

        self._observers[of.name] = of
        foreach(lambda t: t.attach_observer(of), self._transitions.values())
        foreach(lambda p: p.attach_observer(of), self._places.values())
        foreach(lambda t: t.attach_observer(of),
                flatten(map(lambda p: p.tokens, self._places.values())))

    # All arcs connected to a place must have the type of the place
    def add_type(self, type_name: str) -> "TokenType":
        if type_name in self._types:
            raise ValueError(f"Type '{type_name}' is already defined in net "
                             f"'{self.name}'")
        typ = TokenType(type_name, len(self._types), self, )
        self._types[type_name] = typ
        return typ

    def token_type(self, type_name: str) -> "TokenType":
        return self._types[type_name]

    def add_place(self, name, type_name: str = "black dot", queueing_policy_name: str = "FIFO") -> "Place":
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
            place = self._places[name] = klass(name, len(self._places), self._types[type_name])
            foreach(lambda o: place.attach_observer(o),
                    self._observers.values())

            return place

    def place(self, place_name: str) -> "Place":
        return self._places[place_name]

    def _attach_transition_observers(self, t: "Transition"):
        foreach(lambda o: t.attach_observer(o),
                self._observers.values())

    def _validate_transition_name(self, name):
        if name in self._transitions:
            raise ValueError(f"A transition with name '{name}' already exists in net '{self.name}'.")

    # Arcs can be added only to empty input places!
    def add_immediate_transition(self, name: str, priority: int = 1, weight: float = 1.0) -> "Transition":
        if not isinstance(priority, int) or priority < 1:
            raise ValueError(f"The priority of immediate transition '{name}' must be a positive integer")

        if not isinstance(weight, (float, int)) or weight <= 0:
            raise ValueError(f"The weight of immediate transition '{name}' must be a positive float, found {weight}")

        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, len(self._transitions), priority, weight, lambda: 0.0)
        self._attach_transition_observers(t)
        return t

    def add_timed_transition(self, name: str, distribution: "Callable[[], float]") -> "Transition":
        self._validate_transition_name(name)
        self._transitions[name] = t = Transition(name, len(self._transitions), 0, 0.0, distribution)
        self._attach_transition_observers(t)
        return t

    def transition(self, transition_name: str) -> "Transition":
        return self._transitions[transition_name]

    def add_constructor(self, name: str, transition_name: str, output_place_name: str) -> "ConstructorArc":
        return ConstructorArc(name=name,
                              transition=self._transitions[transition_name],
                              output_place=self._places[output_place_name])

    def add_destructor(self, name: str, input_place_name: str, transition_name: str) -> "DestructorArc":
        return DestructorArc(name=name,
                             transition=self._transitions[transition_name],
                             input_place=self._places[input_place_name])

    def add_transfer(self, name: str, input_place_name: str, transition_name: str,
                     output_place_name: str) -> "TransferArc":
        return TransferArc(name=name,
                           transition=self._transitions[transition_name],
                           input_place=self._places[input_place_name],
                           output_place=self._places[output_place_name])

    def add_test(self, name: str, place_name: str, transition_name: str, ) -> "TestArc":
        return TestArc(name=name,
                       transition=self._transitions[transition_name],
                       input_place=self._places[place_name])

    def add_inhibitor(self, name: str, place_name: str, transition_name: str, ) -> "InhibitorArc":
        return InhibitorArc(name=name,
                            transition=self._transitions[transition_name],
                            input_place=self._places[place_name])

    def reset(self):
        """ Remove all tokens from the Petri net & reset the marking-related state of the observers"""
        for place in self._places.values():
            place.reset()

        # Reset the marking-related state
        for observer in self._observers.values():
            observer.reset()


class TokenType:  # dataclasses are not usable with Cython ...
    _name: str
    ordinal: int
    _net: Net

    def __init__(self, name: str, ordinal: int, net: Net):
        self._name = name
        self.ordinal = ordinal
        self._net = net

    @property
    def name(self): return self._name

    @property
    def net(self): return self._net

    def __str__(self):
        return f"{self.__class__.__name__}('{self.name}')"


class Token:
    _typ: TokenType
    _token_observers: "Set[Plugins.AbstractTokenObserver]"
    tags: "Dict[str, Any]"

    def __init__(self, typ: TokenType):
        self._typ = typ
        self._token_observers = set()
        self.tags = dict()
        for of in self.typ.net.observers:
            self.attach_observer(of)

    def attach_observer(self, plugin: Plugins.AbstractPlugin):
        observer = plugin.observe_token(self)

        if observer is not None:
            self._token_observers.add(observer)
            observer.report_construction()

    @property
    def typ(self): return self._typ

    def deposit_at(self, place):  # : "Place"
        for to in self._token_observers:
            to.report_arrival_at(place)

    def remove_from(self, place):  # : "Place"
        for to in self._token_observers:
            to.report_departure_from(place)

    def delete(self):
        for to in self._token_observers:
            to.report_destruction()
        self._token_observers.clear()


# @dataclass
# class Tag:
#     key: str
#     value: Any

@cython.cclass
class Transition:
    _name: str
    ordinal: int
    priority: int
    weight: float
    _distribution: "Callable[[], float]"

    _disabled_arc_count: int
    _arcs: "Dict[str, Arc]"
    _transition_observers: "Set[Plugins.AbstractTransitionObserver]"

    def __init__(self, name: str, ordinal: int, priority: int, weight: float, distribution: "Callable[[], float]"):
        self._name = name
        self.ordinal = ordinal
        self.priority = priority
        self.weight = weight
        self._distribution = distribution
        self._disabled_arc_count = 0
        self._arcs = dict()
        self._transition_observers = set()

    @property
    def name(self) -> str: return self._name

    @property
    def is_timed(self) -> bool:
        return self.priority == 0

    def accept(self, visitor: "PetsiVisitor"):
        visitor.visit(self)

        for arc in self._arcs.values():
            visitor.visit(arc)

    def get_duration(self):
        return self._distribution()

    def attach_observer(self, plugin: "Plugins.AbstractPlugin"):
        observer = plugin.observe_transition(self)

        if observer is not None:
            self._transition_observers.add(observer)

            if self.is_enabled:
                observer.got_enabled()
            else:
                # if not self.is_timed:
                    observer.got_disabled()

    def add_arc(self, arc: "Arc"):
        if arc.name in self._arcs:
            raise ValueError(f"An Arc with name '{arc.name}' already exists on Transition '{self.name}'")

        self._arcs[arc.name] = arc

    @property
    def is_enabled(self) -> bool:
        return self._disabled_arc_count == 0

    @cython.locals(arc="Arc")
    def fire(self):
        assert self.is_enabled, f"Transition '{self._name}' is disabled, it cannot be fired"
        for transition_observer in self._transition_observers:
            transition_observer.before_firing()
        for arc in self._arcs.values():
            arc.flow()
        for transition_observer in self._transition_observers:
            transition_observer.after_firing()

    @cython.cfunc
    @cython.locals(old_disabled_arc_count=int)
    def increment_disabled_arc_count(self):
        old_disabled_arc_count = self._disabled_arc_count
        self._disabled_arc_count += 1

        if old_disabled_arc_count == 0:
            for transition_observer in self._transition_observers:
                transition_observer.got_disabled()

    @cython.cfunc
    def decrement_disabled_arc_count(self):
        self._disabled_arc_count -= 1

        if self._disabled_arc_count == 0:
            for transition_observer in self._transition_observers:
                transition_observer.got_enabled()


class Condition(ABC):
    @property
    @abstractmethod
    def is_true(self) -> bool: pass


class UpdateOp:
    key: str
    new_value: "Any"

    def __init__(self, key: str, new_value: "Any"):
        self.key = key
        self.new_value = new_value

    def apply(self, t: Token): pass


@cython.cclass
class Arc:
    _name: str
    _input_place: "Place" = cython.declare("Place")

    cython.declare(_transition=Transition)
    _transition: Transition

    _output_place: "Place" = cython.declare("Place")

    def __init__(self, name: str, transition: Transition, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self._transition = transition
        self._transition.add_arc(self)

    @property
    def name(self): return self._name

    @property
    def transition(self):return self._transition

    @property
    def typ(self) -> TokenType:
        raise NotImplementedError

    def accept(self, visitor: "PetsiVisitor"):
        visitor.visit(self)

    @property
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @cython.cfunc
    def flow(self):
        """ Move the token among places, according to the type of the arc"""
        raise NotImplementedError


@cython.cclass
class PresenceObserver(Arc):
    """ An Arc-mixin providing the feature of enabling/disabling a transition.

        The arc is notified of the presence of a token at the input place.
        This information is forwarded to the transition so it can manage its enablement status.
    """

    # Transitions track the number of disabled arcs. To match this,
    # we initialize _is_enabled = True.
    # When attaching ourselves to the input place, we get
    # a report_no_token or report_some_token callback so that
    # we can adjust the status and notify the transition, be there need.
    _is_enabled: bool = cython.declare(cython.bint)

    def __init__(self, input_place: "Place", transition: Transition, **kwargs):
        input_place.accept_arc(self, transition.is_timed)
        super().__init__(transition=transition, **kwargs)
        self._input_place = input_place
        self._is_enabled = True
        self._input_place.attach_presence_observer(self)

    @property
    def typ(self) -> TokenType: return self._input_place.typ

    @property
    def input_place(self): return self._input_place

    @property
    def is_enabled(self) -> bool: return self._is_enabled

    @cython.cfunc
    @cython.locals(was_enabled=cython.bint)
    def report_no_token(self):
        was_enabled = self._is_enabled
        self._is_enabled = False

        if was_enabled:
            self._transition.increment_disabled_arc_count()

    @cython.cfunc
    @cython.locals(was_enabled=cython.bint)
    def report_some_token(self):
        was_enabled = self._is_enabled
        self._is_enabled = True

        if not was_enabled:
            self._transition.decrement_disabled_arc_count()


# class TokenPlacer:
#     pass


@cython.cclass
class ConstructorArc(Arc, ):  # TokenPlacer

    def __init__(self, output_place: "Place", **kwargs):
        super().__init__(**kwargs)
        self._output_place = output_place

    @property
    def output_place(self): return self._output_place

    @cython.cfunc
    @cython.locals(token=Token)
    def flow(self):
        token = Token(self._output_place.typ)
        self._output_place.push(token)

    @property
    def typ(self) -> TokenType:
        return self._output_place.typ

    @property
    def is_enabled(self) -> bool: return True


@cython.cclass
class TokenConsumer(PresenceObserver):
    pass
    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)


@cython.cclass
class DestructorArc(TokenConsumer, ):

    @cython.cfunc
    @cython.locals(token=Token)
    def flow(self):
        token = self._input_place.pop()
        token.delete()


@cython.cclass
class TransferArc(TokenConsumer):  # TokenPlacer,

    def __init__(self, name: str, input_place: "Place", output_place: "Place", **kwargs):
        # TODO: should the check happen before object construction?
        if input_place.typ is not output_place.typ:
            raise ValueError(f"Type mismatch on TransferArc('{name}'): "
                             f"type({input_place.name}) is '{input_place.typ.name}' whereas "
                             f"type({output_place.name}) is '{output_place.typ.name}'")
        super().__init__(name=name, input_place=input_place, **kwargs)
        self._output_place = output_place  # output_place=output_place,

    @property
    def output_place(self): return self._output_place

    @cython.cfunc
    @cython.locals(token=Token)
    def flow(self):
        token = self._input_place.pop()
        self._output_place.push(token)


@cython.cclass
class TestArc(PresenceObserver):
    @cython.cfunc
    def flow(self):
        pass


@cython.cclass
class InhibitorArc(TestArc):
    @cython.cfunc
    def report_some_token(self):
        # Cannot use super() in a cython extension class
        TestArc.report_no_token(self)

    @cython.cfunc
    def report_no_token(self):
        # Cannot use super() in a cython extension class
        TestArc.report_some_token(self)


class Place:
    _name: str
    ordinal: int
    _typ:  TokenType
    _tokens: "Deque[Token]"
    _place_observers: "Set[Plugins.AbstractPlaceObserver]"
    _presence_observers: "Set[PresenceObserver]"

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

    _status: _Status

    def __init__(self, name: str, ordinal: int, typ:  TokenType, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self.ordinal = ordinal
        self._typ = typ
        self._status = self._Status.UNDEFINED
        self._tokens = collections.deque()
        self._place_observers = set()
        self._presence_observers = set()

    @property
    def name(self): return self._name

    def accept(self, visitor: "PetsiVisitor"):
        visitor.visit(self)

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
    def typ(self): return self._typ

    def reset(self):
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

        #foreach(lambda po: po.report_departure_of(token), self._place_observers)
        for place_observer in self._place_observers:
            place_observer.report_departure_of(token)

        # foreach(lambda po: po.report_no_token(), self._presence_observers)
        if self.is_empty:
            for presence_observer in self._presence_observers:
                presence_observer.report_no_token()

        return token

    def push(self, token):   # "Token"
        was_empty = self.is_empty

        # Move_to_place notifies observers. To show them a consistent picture,
        # we first update the place, only then call move_to_place
        self._push(token)
        token.deposit_at(self)

        for place_observer in self._place_observers:
            place_observer.report_arrival_of(token)

        if was_empty:
            for presence_observer in self._presence_observers:
                presence_observer.report_some_token()

    def _is_empty(self):
        return  len(self._tokens) == 0

    @property
    def is_empty(self):
        return self._is_empty()

    @property
    def tokens(self) -> "Iterator[Token]":
        return iter(self._tokens)

    def _pop(self) -> Token:
        return self._tokens.popleft()

    def _push(self, t):   # : Token
        self._tokens.append(t)  # Appends to the right


FIFOPlace = Place


@cython.cclass
class LIFOPlace(Place):
    @cython.ccall
    def _push(self, t: Token):
        self._tokens.appendleft(t)


class PetsiVisitor(ABC):
    @abstractmethod
    def visit(self, visitable: Union[Net, Transition, Place, Arc]):
        pass
