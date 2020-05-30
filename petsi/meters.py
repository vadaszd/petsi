from array import array
from typing import TYPE_CHECKING, FrozenSet, Optional, Dict

from .fire_control import Clock

if TYPE_CHECKING:
    from . import Structure, Plugins


class GenericCollector:
    def __init__(self, required_observations):
        self.required_observations = required_observations
        self._arrays = dict()
        self.reset()

    def reset(self):
        self._arrays.clear()
        self._arrays.update((field_name, array(type_code)) for field_name, type_code in self._type_codes.items())
        # noinspection PyAttributeOutsideInit
        self._any_array = next(iter(self._arrays.values()))    # for calculating the number of observations

    def get_observations(self) -> Dict[str, array]:
        data = self._arrays.copy()
        self.reset()
        return data

    def need_more_observations(self) -> bool:
        return len(self._any_array) < self.required_observations


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

    def __init__(self, _plugin: "Plugins.Plugin", _place: "Structure.Place", _clock: Clock,
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

    def __init__(self, _plugin: "Plugins.Plugin", _token: "Structure.Token",
                 _places: Optional[FrozenSet[int]], _clock: Clock, _collector: SojournTimeCollector, _token_id: int):
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

    def report_arrival_at(self, _: "Structure.Place"):
        """ Start timer for place"""
        # if self._places is None or p.ordinal in self._places:
        self._arrival_time = self._clock.read()

    def report_departure_from(self, p: "Structure.Place"):
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


class FiringCollector(GenericCollector):
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

    def __init__(self, _plugin: "Plugins.Plugin", _transition: "Structure.Transition", _clock: Clock,
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
