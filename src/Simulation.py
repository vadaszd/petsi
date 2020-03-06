from dataclasses import dataclass


@dataclass
class ESPNObserver:
    currentTime: float


class TransitionObserver: pass


@dataclass
class TokenObserver:
    creationTime: float
    arrivalTime: float


ESPNObserver *-- "*" TransitionObserver
ESPNObserver *-- "*" TokenObserver
ESPNObserver *-- "*" PlaceObserver
ESPNObserver ..|> Plugins.Observer
TransitionObserver ..|> Plugins.TransitionObserver
TokenObserver ..|> Plugins.TokenObserver
PlaceObserver ..|> Plugins.PlaceObserver
