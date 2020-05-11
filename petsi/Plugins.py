from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from typing import TYPE_CHECKING, Dict, Set, Optional, TypeVar, Generic, Type, Union

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from . import Structure


_PlaceObserver = TypeVar("_PlaceObserver", bound="AbstractPlaceObserver")
_TransitionObserver = TypeVar("_TransitionObserver", bound="AbstractTransitionObserver")
_TokenObserver = TypeVar("_TokenObserver", bound="AbstractTokenObserver")
Plugin = TypeVar("Plugin", bound="AbstractPlugin")


@dataclass(eq=False)
class AbstractPlaceObserver(ABC, Generic[Plugin]):
    _plugin: Plugin
    _place: "Structure.Place"

    @abstractmethod
    def report_arrival_of(self, token): pass

    @abstractmethod
    def report_departure_of(self, token): pass


@dataclass(eq=False)
class AbstractTransitionObserver(ABC, Generic[Plugin]):
    _plugin: Plugin
    _transition: "Structure.Transition"

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
class AbstractTokenObserver(ABC, Generic[Plugin]):
    _plugin: Plugin
    _token: "Structure.Token"

    @abstractmethod
    def report_construction(self, ): pass

    @abstractmethod
    def report_destruction(self, ): pass

    @abstractmethod
    def report_arrival_at(self, p: "Structure.Place"): pass

    @abstractmethod
    def report_departure_from(self, p: "Structure.Place"): pass


@dataclass(eq=False)
class AbstractPlugin(ABC, Generic[_PlaceObserver, _TransitionObserver, _TokenObserver]):
    name: str

    _place_observers: Dict[str, _PlaceObserver] = field(default_factory=dict, init=False)
    _transition_observers: Dict[str, _TransitionObserver] = field(default_factory=dict, init=False)
    _token_observers: Set[_TokenObserver] = field(default_factory=set, init=False)

    # In derived classes of AbstractPlugin one may override these factory method
    # to return instances of classes inheriting from
    # `AbstractPlaceObserver`, `AbstractTransitionObserver` and `AbstractTokenObserver`.
    # In these factory methods you can adopt the constructors of the derived classes
    # to the uniform interface the rest of the plugin code assumes.
    def place_observer_factory(self, p: "Structure.Place") -> Optional[_PlaceObserver]: pass

    def token_observer_factory(self, t: "Structure.Token") -> Optional[_TokenObserver]: pass

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional[_TransitionObserver]: pass

    def observe_place(self, p: "Structure.Place") -> Optional[AbstractPlaceObserver]:
        o = self.place_observer_factory(p)

        if o is not None:
            self._place_observers[p.name] = o

        return o

    def observe_token(self, t: "Structure.Token") -> Optional[AbstractTokenObserver]:
        o = self.token_observer_factory(t)

        if o is not None:
            self._token_observers.add(o)

        return o

    def observe_transition(self, t: "Structure.Transition") -> Optional[AbstractTransitionObserver]:
        o = self.transition_observer_factory(t)

        if o is not None:
            self._transition_observers[t.name] = o

        return o


class NoopPlaceObserver(AbstractPlaceObserver, Generic[Plugin]):

    def report_arrival_of(self, token):
        pass

    def report_departure_of(self, token):
        pass


class NoopTransitionObserver(AbstractTransitionObserver, Generic[Plugin]):

    def after_firing(self):
        pass

    def got_enabled(self):
        pass

    def got_disabled(self):
        pass

    def before_firing(self):
        pass


class NoopTokenObserver(AbstractTokenObserver, Generic[Plugin]):

    def report_construction(self):
        pass

    def report_destruction(self):
        pass

    def report_arrival_at(self, p: "Structure.Place"):
        pass

    def report_departure_from(self, p: "Structure.Place"):
        pass


