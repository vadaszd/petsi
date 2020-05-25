from dataclasses import field, dataclass
from functools import cached_property
from itertools import repeat
from typing import Optional

from .Plugins import AbstractPlugin, NoopPlaceObserver, NoopTokenObserver

from . import Structure

from .fire_control import AutoFirePluginTransitionObserver, FireControl, Clock
from .util import foreach


@dataclass(eq=False)
class AutoFirePlugin(
        AbstractPlugin[NoopPlaceObserver, AutoFirePluginTransitionObserver, NoopTokenObserver]):

    """ A PetSi plugin for firing transitions automatically.

        The transitions are selected for firing based on the rules for
        Extended Stochastic Petri Nets.
    """

    _fire_control: FireControl = field(default_factory=FireControl, init=False)

    @cached_property
    def clock(self) -> Clock:
        return self._fire_control.get_clock()

    def reset(self): self._fire_control.reset()

    def fire_until(self, end_time: float):
        clock: Clock = self.clock
        self._fire_control.start()

        while clock.read() < end_time:
            self._fire_control.fire_next()

    def fire_repeatedly(self, count_of_firings: int = 0):
        self._fire_control.start()

        foreach(lambda _: self._fire_control.fire_next(),
                repeat(None) if count_of_firings == 0 else repeat(None, count_of_firings))

    def transition_observer_factory(self, t: "Structure.Transition") -> Optional[AutoFirePluginTransitionObserver]:
        return AutoFirePluginTransitionObserver(self, t, self._fire_control)


