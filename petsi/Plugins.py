from abc import ABC, abstractmethod
from dataclasses import dataclass

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from petsi import Structure


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


@dataclass
class Observer(ABC):
    name: str

    @abstractmethod
    def observe_place(self, p: "Structure.Place") -> PlaceObserver: pass

    @abstractmethod
    def observe_token(self, t: "Structure.Token") -> TokenObserver: pass

    @abstractmethod
    def observe_transition(self, t: "Structure.Transition") -> TransitionObserver: pass

