""" The interface for PetSi plugins.

    On a high level, a plugin is a :class:`class <AbstractPlugin>` with factory methods for creating
        - :class:`place observers <AbstractPlaceObserver>`
        - :class:`transition observers <AbstractTransitionObserver>` and
        - :class:`token observers <AbstractTokenObserver>`

    To create a new plugin, you need to create implementations of the classes and methods defined here.
    If your plugin needs to implement some of the methods only, you can reuse the ``Noop...``
    implementation classes.

    How Petsi interacts with the plugins is described on the :doc:`Design` page.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from typing import TYPE_CHECKING, Dict, Set, Optional, TypeVar, Generic

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from ..._structure import Place, Transition, Token


APlaceObserver = TypeVar("APlaceObserver", bound="AbstractPlaceObserver")
ATransitionObserver = TypeVar("ATransitionObserver", bound="AbstractTransitionObserver")
ATokenObserver = TypeVar("ATokenObserver", bound="AbstractTokenObserver")
APlugin = TypeVar("APlugin", bound="AbstractPlugin")


@dataclass(eq=False)
class AbstractPlaceObserver(ABC, Generic[APlugin]):
    """ The interface for all place observers.

    Place observers can be used to accumulate observation state related to a place.
    They get notifications related to the observed place.

    :param _plugin: The plugin this observer belongs to.
    :type _plugin: :class:`Plugins.AbstractPlugin`
    :param _place: The place observed by this observer.
    :type _place: :class:`_structure.Place`
    """
    _plugin: APlugin
    _place: "Place"

    @abstractmethod
    def reset(self):
        """ Reset the observer.

        When this method is invoked, all marking related state must be removed from the observer.
        """

    @abstractmethod
    def report_arrival_of(self, token):
        """ Report the arrival of a token at the observed place.

        Petsi will invoke this method whenever a token arrives at the observed state.
        """

    @abstractmethod
    def report_departure_of(self, token):
        """ Report the departure of a token from the observed place.

        Petsi will invoke this method whenever a token departs from the observed state.
        """


@dataclass(eq=False)
class AbstractTransitionObserver(ABC, Generic[APlugin]):
    """ The interface for all transition observers.

    Transition observers accumulate observation state related to a transition.
    They get notifications related to the observed transition.

    :param _plugin: The plugin this observer belongs to.
    :type _plugin: :class:`Plugins.AbstractPlugin`
    :param _transition: The transition observed by this observer.
    :type _transition: :class:`_structure.Transition`
    """
    _plugin: APlugin
    _transition: "Transition"

    @abstractmethod
    def reset(self):
        """ Reset the observer.

        When this method is invoked, all marking related state must be removed from the observer.
        """

    @abstractmethod
    def before_firing(self, ):
        """ A callback to notify about the start of the firing process.

        Petsi will invoke this method before each firing.
        """

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
class AbstractTokenObserver(ABC, Generic[APlugin]):
    """ The interface for all token observers.

    Token observers accumulate observation state related to a token.
    They get notifications related to the observed token.

    :param _plugin: The plugin this observer belongs to.
    :type _plugin: :class:`Plugins.AbstractPlugin`
    :param _token: The token observed by this observer.
    :type _token: :class:`_structure.Token`
    """
    _plugin: APlugin
    _token: "Token"

    @abstractmethod
    def reset(self):
        """ Reset the observer.

        When this method is invoked, all marking related state must be removed from the observer.
        """

    @abstractmethod
    def report_construction(self, ):
        """ Report the construction of the token.

        Petsi will invoke this method after the token and its observers are constructed.
        """

    @abstractmethod
    def report_destruction(self, ):
        """ Report the destruction of the token.

        Petsi will invoke this method before the token is destroyed.
        """

    @abstractmethod
    def report_arrival_at(self, p: "Place"):
        """ Report the arrival of the token at the given place.

        Petsi will invoke this method after the token and its observers are constructed.
        """

    @abstractmethod
    def report_departure_from(self, p: "Place"): pass


@dataclass(eq=False)
class AbstractPlugin(ABC, Generic[APlaceObserver, ATransitionObserver, ATokenObserver]):
    """ The interface for all Petsi plugins.

    This class defines the interface for creating place, transition and token observers and
    manages the marking related state of the observers.

    :param name: The name of the plugin.
    :type name: str
    """
    name: str = field()

    _place_observers: Dict[str, APlaceObserver] = field(default_factory=dict, init=False)
    _transition_observers: Dict[str, ATransitionObserver] = field(default_factory=dict, init=False)
    _token_observers: Set[ATokenObserver] = field(default_factory=set, init=False)

    # In derived classes of AbstractPlugin one may override these factory methods
    # to return instances of classes inheriting from
    # `AbstractPlaceObserver`, `AbstractTransitionObserver` and `AbstractTokenObserver`.
    # In these factory methods you can adopt the constructors of the derived classes
    # to the uniform interface the rest of the plugin code assumes.
    def place_observer_factory(self, p: "Place") -> Optional[APlaceObserver]:
        """ Create a place observer implementation.

        Override this method to create a place observer implementation.

        Petsi will invoke this method for the places of the net that were selected for observation.
        The method should return a place observer or ``None`` if the plugin is not interested in observing places.

        :param p: The :class:`~petsi._structure.Place` to observe.
        :return: A place observer or ``None``
        """

    def token_observer_factory(self, t: "Token") -> Optional[ATokenObserver]:
        """ Create a token observer implementation.

        Override this method to create a token observer implementation.

        Petsi will invoke this method for the tokens of the net that were selected for observation.
        The method should return a token observer or ``None`` if the plugin is not interested in observing tokens.

        :param t: The :class:`~petsi._structure.Token` to observe.
        :return: A token observer or ``None``
        """

    def transition_observer_factory(self, t: "Transition") -> Optional[ATransitionObserver]:
        """ Create a transition observer implementation.

        Override this method to create a transition observer implementation.

        Petsi will invoke this method for the transition of the net that were selected for observation.
        The method should return a transition observer or ``None`` if the plugin is not interested in observing
        transitions.

        :param t: The :class:`~petsi._structure.Token` to observe.
        :return: A token observer or ``None``
        """

    def reset(self):
        # """ Reset the marking-related state of the plugin.
        #
        # Removes all data collected during the previous simulation
        # by cascading the call to the observers of the plugin.
        # """
        for token_observer in self._token_observers:
            token_observer.reset()
        self._token_observers.clear()

        for place_observer in self._place_observers.values():
            place_observer.reset()

        for transition_observer in self._transition_observers.values():
            transition_observer.reset()

    def observe_place(self, p: "Place") -> Optional[AbstractPlaceObserver]:
        o = self.place_observer_factory(p)

        if o is not None:
            self._place_observers[p.name] = o

        return o

    def observe_token(self, t: "Token") -> Optional[AbstractTokenObserver]:
        o = self.token_observer_factory(t)

        if o is not None:
            self._token_observers.add(o)

        return o

    def observe_transition(self, t: "Transition") -> Optional[AbstractTransitionObserver]:
        o = self.transition_observer_factory(t)

        if o is not None:
            self._transition_observers[t.name] = o

        return o


class NoopPlaceObserver(AbstractPlaceObserver, Generic[APlugin]):
    """ A place observer implementation that does nothing."""

    def reset(self):
        """ Does nothing."""

    def report_arrival_of(self, token):
        """ Does nothing."""

    def report_departure_of(self, token):
        """ Does nothing."""


class NoopTransitionObserver(AbstractTransitionObserver, Generic[APlugin]):
    """ A transition observer implementation that does nothing."""

    def reset(self):
        """ Does nothing."""

    def after_firing(self):
        """ Does nothing."""

    def got_enabled(self):
        """ Does nothing."""

    def got_disabled(self):
        """ Does nothing."""

    def before_firing(self):
        """ Does nothing."""


class NoopTokenObserver(AbstractTokenObserver, Generic[APlugin]):
    """ A token observer implementation that does nothing."""

    def reset(self):
        """ Does nothing."""

    def report_construction(self):
        """ Does nothing."""

    def report_destruction(self):
        """ Does nothing."""

    def report_arrival_at(self, p: "Place"):
        """ Does nothing."""

    def report_departure_from(self, p: "Place"):
        """ Does nothing."""


