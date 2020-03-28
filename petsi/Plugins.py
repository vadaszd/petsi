from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from typing import TYPE_CHECKING, Dict, Set, Optional

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
    def before_firing(self, ):
        """ This callback notifies about the start of the firing process."""

    @abstractmethod
    def after_firing(self, ):
        """ This callback notifies about the end of the firing process."""

    @abstractmethod
    def got_enabled(self, ):
        """ Signals that all arcs are enabled and the transition can be fired."""

    @abstractmethod
    def got_disabled(self, ):
        """ Indicates that some of the arcs got disabled and the transition no longer can be fired.

            This call back is called only if there was a matching `got_enabled()`
            call and the transition has not been fired since.

            It is not called if the transition gets disabled by firing.
        """


@dataclass(eq=False)
class AbstractPlugin(ABC):
    name: str

    _place_observers: Dict[str, PlaceObserver] = field(init=False)
    _transition_observers: Dict[str, TransitionObserver] = field(init=False)
    _token_observers: Set[TokenObserver] = field(init=False)

    @abstractmethod
    def place_observer_factory(self, p: "Structure.Place") -> Optional[PlaceObserver]: pass

    @abstractmethod
    def token_observer_factory(self, t: "Structure.Token") -> Optional[TokenObserver]: pass

    @abstractmethod
    def transition_observer_factory(self, t: "Structure.Transition") -> Optional[TransitionObserver]: pass

    def observe_place(self, p: "Structure.Place") -> Optional[PlaceObserver]:
        o = self.place_observer_factory(p)

        if o is not None:
            self._place_observers[p.name] = o

        return o

    def observe_token(self, t: "Structure.Token") -> Optional[TokenObserver]:
        o = self.token_observer_factory(t)

        if o is not None:
            self._token_observers.add(o)

        return o

    def observe_transition(self, t: "Structure.Transition") -> Optional[TransitionObserver]:
        o = self.transition_observer_factory(t)

        if o is not None:
            self._transition_observers[t.name] = o

        return o
