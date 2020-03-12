from . import Plugins

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Structure


@dataclass(eq=False)
class ESPNPlugin(Plugins.AbstractPlugin):
    currentTime: float = field(default=0.0)

    def place_observer_factory(self, p: "Structure.Place") -> Plugins.PlaceObserver:
        return PlaceObserver(p)

    def token_observer_factory(self, t: "Structure.Token") -> Plugins.TokenObserver:
        return TokenObserver(t)

    def transition_observer_factory(self, t: "Structure.Transition") -> Plugins.TransitionObserver:
        return TransitionObserver(t)


@dataclass(eq=False)
class PlaceObserver(Plugins.PlaceObserver):
    place: "Structure.Place"

    def report_arrival_of(self, token): pass

    def report_departure_of(self, token): pass


@dataclass(eq=False)
class TransitionObserver(Plugins.TransitionObserver):
    transition: "Structure.Transition"

    def before_firing(self, ): pass

    def after_firing(self, ): pass

    def got_enabled(self, ): pass

    def got_disabled(self, ): pass


@dataclass(eq=False)
class TokenObserver(Plugins.TokenObserver):
    token: "Structure.Token"
    creationTime: float = field(init=False)
    arrivalTime: float = field(init=False)

    def report_construction(self, ): pass

    def report_destruction(self, ): pass

    def report_arrival_at(self, p: "Structure.Place"): pass

    def report_departure_from(self, p: "Structure.Place"): pass

# ESPNPlugin *-- "*" TransitionObserver
# ESPNPlugin *-- "*" TokenObserver
# ESPNPlugin *-- "*" PlaceObserver
# ESPNPlugin ..|> Plugins.AbstractPlugin
# TransitionObserver ..|> Plugins.TransitionObserver
# TokenObserver ..|> Plugins.TokenObserver
# PlaceObserver ..|> Plugins.PlaceObserver
