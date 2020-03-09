from dataclasses import dataclass, field

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import TYPE_CHECKING, Set, Dict
    from petsi import Structure, Plugins


@dataclass
class ESPNObserver(Plugins.Observer):
    currentTime: float = field(default=0.0)
    _place_observers: Dict[str, PlaceObserver] = field(init=False)
    _transition_observers: Dict[str, TransitionObserver] = field(init=False)
    _token_observers: Set[TokenObserver] = field(init=False)

    def observe_place(self, p: "Structure.Place") -> Plugins.PlaceObserver:
        self._place_observers[p.name] = o = PlaceObserver(p)
        return o

    def observe_token(self, t: "Structure.Token") -> Plugins.TokenObserver:
        o = TokenObserver(t)
        self._token_observers.add(o)
        return o

    def observe_transition(self, t: "Structure.Transition") -> Plugins.TransitionObserver:
        self._transition_observers[t.name] = o = TransitionObserver(t)
        return o


@dataclass
class PlaceObserver(Plugins.PlaceObserver):
    place: "Structure.Place"

    def report_arrival_of(self, token): pass

    def report_departure_of(self, token): pass


@dataclass
class TransitionObserver(Plugins.TransitionObserver):
    transition: "Structure.Transition"

    def before_firing(self, ): pass

    def after_firing(self, ): pass

    def got_enabled(self, ): pass

    def got_disabled(self, ): pass


@dataclass
class TokenObserver(Plugins.TokenObserver):
    token: "Structure.Token"
    creationTime: float = field(init=False)
    arrivalTime: float = field(init=False)

    def report_construction(self, ): pass

    def report_destruction(self, ): pass

    def report_arrival_at(self, p: "Structure.Place"): pass

    def report_departure_from(self, p: "Structure.Place"): pass

# ESPNObserver *-- "*" TransitionObserver
# ESPNObserver *-- "*" TokenObserver
# ESPNObserver *-- "*" PlaceObserver
# ESPNObserver ..|> Plugins.Observer
# TransitionObserver ..|> Plugins.TransitionObserver
# TokenObserver ..|> Plugins.TokenObserver
# PlaceObserver ..|> Plugins.PlaceObserver
