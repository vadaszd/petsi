""" A skeleton for plugins collecting statistics on the activities in a Petri net.
"""

from array import array
from dataclasses import dataclass, field
from typing import Generic, TypeVar, TYPE_CHECKING

from ..util import export

from ._meters import GenericCollector
from .Plugins import APlaceObserver, ATransitionObserver, ATokenObserver, AbstractPlugin

if TYPE_CHECKING:
    from .autofire import Clock
    from typing import Optional, FrozenSet, Dict, Callable

ACollector = TypeVar("ACollector", bound=GenericCollector)


@export
@dataclass(eq=False)
class MeterPlugin(Generic[ACollector, APlaceObserver, ATransitionObserver, ATokenObserver],  #
                  AbstractPlugin[APlaceObserver, ATransitionObserver, ATokenObserver],
                  ):
    """ Base class for plugins collecting observations."""
    _n: int                                       # number of observations to collect
    _places: "Optional[FrozenSet[int]]"           # Observe these places only
    _token_types: "Optional[FrozenSet[int]]"      # Observe these token types only
    _transitions: "Optional[FrozenSet[int]]"      # Observe these transitions only
    _clock: "Clock"

    _collector: ACollector = field(init=False)

    def get_observations(self) -> "Dict[str, array]":
        """ Retrieve the collected observations.

        As this method is relatively expensive, it should be called only when polling
        indicates that.
        For polling use the callable returned by :meth:`get_need_more_observations`.
        """
        return self._collector.get_observations()

    def get_need_more_observations(self) -> "Callable[[], bool]":
        """ :return: a callable for polling if :meth:`get_observations` should be called."""
        return self._collector.need_more_observations

    @property
    def required_observations(self) -> int:
        """ The number of observations to collect before the need to call :meth:`get_observations` is indicated."""
        return self._collector.required_observations

    @required_observations.setter
    def required_observations(self, required_observations: int):
        self._collector.required_observations = required_observations


