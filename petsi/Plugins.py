from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from typing import TYPE_CHECKING, Dict, Set

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from . import Structure


class PlaceObserver(ABC):

    @abstractmethod
    def report_arrival_of(self, token): pass

    @abstractmethod
    def report_departure_of(self, token): pass


class TokenObserver(ABC):

    @abstractmethod
    def report_construction(self, ): pass

    @abstractmethod
    def report_destruction(self, ): pass

    @abstractmethod
    def report_arrival_at(self, p: "Structure.Place"): pass

    @abstractmethod
    def report_departure_from(self, p: "Structure.Place"): pass


class TransitionObserver(ABC):
    @abstractmethod
    def before_firing(self, ): pass

    @abstractmethod
    def after_firing(self, ): pass

    @abstractmethod
    def got_enabled(self, ): pass

    @abstractmethod
    def got_disabled(self, ): pass


@dataclass(eq=False)
class AbstractPlugin(ABC):
    name: str

    _place_observers: Dict[str, PlaceObserver] = field(init=False)
    _transition_observers: Dict[str, TransitionObserver] = field(init=False)
    _token_observers: Set[TokenObserver] = field(init=False)

    @abstractmethod
    def place_observer_factory(self, p: "Structure.Place") -> PlaceObserver: pass

    @abstractmethod
    def token_observer_factory(self, t: "Structure.Token") -> TokenObserver: pass

    @abstractmethod
    def transition_observer_factory(self, t: "Structure.Transition") -> TransitionObserver: pass

    def observe_place(self, p: "Structure.Place") -> PlaceObserver:
        self._place_observers[p.name] = o = self.place_observer_factory(p)
        return o

    def observe_token(self, t: "Structure.Token") -> TokenObserver:
        o = self.token_observer_factory(t)
        self._token_observers.add(o)
        return o

    def observe_transition(self, t: "Structure.Transition") -> TransitionObserver:
        self._transition_observers[t.name] = o = self.transition_observer_factory(t)
        return o
