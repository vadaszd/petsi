from typing import TYPE_CHECKING

from .._meters import GenericCollector

if TYPE_CHECKING:
    # Need to rename Clock, otherwise it collides with the cimported Clock in the .pxd file!
    from ..autofire import Clock as TClock

    # Same trick for Transition
    from ..._structure import Transition as TTransition

    from ..interface import APlugin


class FiringCollector(GenericCollector):
    """ Collect data about the firings of transitions when the firing is completed.

    For an overview see :ref:`collecting-simulation-data`.

    .. rubric:: Structure of the observations collected
    .. csv-table::
        :header:  Field name, Data type, Description
        :widths: auto

        ``transition`` ,``unsigned int (16 bits)`` , The index of the transition fired
        ``firing_time`` , ``double`` , When transition was fired
        ``interval`` , ``double`` , The time elapsed since the previous firing of the transition

    """
    _type_codes = dict(transition='I',   # unsigned int (16 bits)
                       firing_time='d',  # double
                       interval='d',     # double
                       )

    def reset(self):
        super().reset()
        # noinspection PyAttributeOutsideInit
        self._transition, self._firing_time, self._interval = self._arrays.values()

    # cython crashes with argument annotations ....
    # def collect(self, transition: int, firing_time: float, interval: float):
    def collect(self, transition, firing_time, interval):
        self._transition.append(transition)
        self._firing_time.append(firing_time)
        self._interval.append(interval)


class TransitionIntervalPluginTransitionObserver:

    _previous_firing_time: float
    _collector: FiringCollector

    def __init__(self, _plugin: "APlugin", _transition: "TTransition", _clock: "TClock",
                 _collector: FiringCollector):
        self._plugin = _plugin
        self._transition = _transition
        self._clock = _clock
        self._collector = _collector
        self.reset()

    def got_enabled(self, ): pass   # No actual base class, so need to provide an implementation

    def got_disabled(self, ): pass  # No actual base class, so need to provide an implementation

    def before_firing(self): pass   # No actual base class, so need to provide an implementation

    def after_firing(self, ):
        current_time = self._clock.read()
        interval = current_time - self._previous_firing_time
        self._collector.collect(self._transition.ordinal, self._clock.read(), interval, )
        self._previous_firing_time = current_time

    def reset(self):
        self._previous_firing_time = self._clock.read()
