from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    import Structure


class PlaceObserver(ABC):
    def report_arrival_of(self, token): pass
    def report_departure_of(self, token): pass


class TokenObserver(ABC):
    def report_construction(self, ): pass
    def report_destruction(self, ): pass
    def report_arrival_at(self, p: "Structure.Place"): pass
    def report_departure_from(self, p: "Structure.Place"): pass


class TransitionObserver(ABC):
    def before_firing(self, ): pass
    def after_firing(self, ): pass
    def got_enabled(self, ): pass
    def got_disabled(self, ): pass


class Observer(ABC):
    name: str
    def observe_place(self, p: "Structure.Place") -> PlaceObserver: pass
    def observe_token(self, t: "Structure.Token") -> TokenObserver: pass
    def observe_transition(self, t: "Structure.Transition") -> TransitionObserver: pass

