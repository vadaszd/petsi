from typing import TYPE_CHECKING

from .._meters import GenericCollector

if TYPE_CHECKING:
    from typing import Optional, FrozenSet

    # Need to rename Clock, otherwise it collides with the cimported Clock in the .pxd file!
    from ..autofire import Clock as TClock

    # Same trick for Token and Place
    from ..._structure import Token as TToken, Place as TPlace

    from ..Plugins import APlugin


class SojournTimeCollector(GenericCollector):
    _type_codes = dict(token_id='Q',     # unsigned long long (64 bits)
                       token_type='I',   # unsigned int (16 bits)
                       start_time='d',   # double
                       transitions='Q',  # unsigned long long (64 bits)
                       place='I',        # unsigned int (16 bits)
                       duration='d',     # double
                       )

    def reset(self):
        super().reset()
        # noinspection PyAttributeOutsideInit
        self._token_id, self._token_type, self._start_time, self._num_transitions, self._place, self._duration = \
            self._arrays.values()

    # cython crashes with argument annotations ....
    # def collect(self, token_id: int, token_type: int, start_time: float,
    #             num_transitions: int, place: int, duration: float):
    def collect(self, token_id, token_type, start_time,
                num_transitions, place, duration):
        self._token_id.append(token_id)
        self._token_type.append(token_type)
        self._start_time.append(start_time)
        self._num_transitions.append(num_transitions)
        self._place.append(place)
        self._duration.append(duration)


class SojournTimePluginTokenObserver:  # Cython does not cope with base classes here

    def __init__(self,
                 _plugin: "APlugin",
                 _token: "TToken",
                 _places: "Optional[FrozenSet[int]]",
                 _clock: "TClock",
                 _collector: SojournTimeCollector,
                 _token_id: int):
        self._plugin = _plugin
        self._token = _token
        self._token_id = _token_id
        self._transition_count = 0
        self._places = _places
        self._clock = _clock
        self._collector = _collector
        self._arrival_time = 0.0

    def reset(self):
        # The observed token will anyway be removed, together with us...
        pass

    def report_construction(self):
        pass

    def report_destruction(self):
        pass

    def report_arrival_at(self, _: "TPlace"):
        """ Start timer for place"""
        # if self._places is None or p.ordinal in self._places:
        self._arrival_time = self._clock.read()

    def report_departure_from(self, p: "TPlace"):
        """ Stop timer and compute the sojourn time.
            Select the bucket of the per visit histogram that belongs
            to the place and increment it.
            Add s.t. for the overall sojourn time of the token for this place
        """
        if self._places is None or p.ordinal in self._places:
            current_time: float = self._clock.read()
            sojourn_time: float = current_time - self._arrival_time
            self._collector.collect(self._token_id, self._token.typ.ordinal, self._arrival_time,
                                    self._transition_count, p.ordinal, sojourn_time)
