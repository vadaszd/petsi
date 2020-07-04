from typing import TYPE_CHECKING

from .._meters import GenericCollector

if TYPE_CHECKING:
    # Need to rename Clock, otherwise it collides with the cimported Clock in the .pxd file!
    from ..autofire import Clock as TClock

    # Same trick for Place
    from ..._structure import Place as TPlace

    from ..Plugins import APlugin


class TokenCounterCollector(GenericCollector):
    _type_codes = dict(start_time='d',   # double
                       place='I',        # unsigned int (16 bits)
                       count='Q',        # unsigned long long (64 bits)
                       duration='d',     # double
                       )

    def reset(self):
        super().reset()
        # noinspection PyAttributeOutsideInit
        self._start_time, self._place, self._count, self._duration = self._arrays.values()

    # cython crashes with argument annotations ....
    # def collect(self, start_time: float, place: int, count: int, duration: float):
    def collect(self, start_time, place, count, duration):
        self._start_time.append(start_time)
        self._place.append(place)
        self._count.append(count)
        self._duration.append(duration)


class TokenCounterPluginPlaceObserver:

    def __init__(self, _plugin: "APlugin", _place: "TPlace", _clock: "TClock",
                 _collector: TokenCounterCollector):
        self._plugin = _plugin
        self._place = _place
        self._clock = _clock
        self._collector = _collector
        self._num_tokens = 0
        self._time_of_last_token_move = 0.0
        # self._time_having: List[float] = list()

    def reset(self):
        self._num_tokens = 0
        self._time_of_last_token_move = 0.0

    def _update_num_tokens_by(self, delta: int):
        now: float = self._clock.read()
        duration: float = now - self._time_of_last_token_move

        self._collector.collect(self._time_of_last_token_move, self._place.ordinal, self._num_tokens, duration)

        self._time_of_last_token_move = now
        self._num_tokens += delta
        # Cannot go negative
        assert self._num_tokens >= 0

    def report_arrival_of(self, _):
        self._update_num_tokens_by(+1)

    def report_departure_of(self, _):
        self._update_num_tokens_by(-1)
