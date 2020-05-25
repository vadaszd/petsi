from .fire_control cimport Clock
from .Structure cimport Transition, Token, Place
from cpython cimport iterator
from cpython.array cimport array

import cython


cdef class GenericCollector:
    # cdef dict _type_codes  #: Dict[str, str]
    cdef dict _arrays      #: Dict[str, array]

    # def reset(self)
    # cpdef get_observations(self) -> Dict[str, array]


cdef class TokenCounterCollector(GenericCollector):
    cdef array _start_time
    cdef array _place
    cdef array _count
    cdef array _duration

    cdef collect(self, double start_time, unsigned int place, unsigned long long count, double duration)


cdef class TokenCounterPluginPlaceObserver:
    cdef object _plugin      #: Plugin
    cdef Place _place        #: "Structure.Place" = cython.declare("Structure.Place")
    cdef Clock _clock
    cdef TokenCounterCollector _collector

    cdef int _num_tokens       #: int = cython.declare(cython.int)

    cdef float _time_of_last_token_move    # : float = cython.declare(cython.float)

    cdef list _time_having      # : List[float] = cython.declare(list)


    @cython.locals(now=cython.float, duration=cython.float)
    cdef _update_num_tokens_by(self, int delta)

    cpdef report_arrival_of(self, token)

    cpdef report_departure_of(self, token)


cdef class SojournTimeCollector(GenericCollector):
    cdef array _token_id
    cdef array _token_type
    cdef array _start_time
    cdef array _num_transitions
    cdef array _place
    cdef array _duration

    cdef collect(self, unsigned long long token_id,
                       unsigned int token_type,
                       double start_time,
                       unsigned long long transitions,
                       unsigned int place, double duration)


cdef class SojournTimePluginTokenObserver:
    cdef object _plugin   # Plugins.Plugin
    cdef Token _token
    cdef unsigned long long _token_id
    cdef unsigned long long _transition_count
    cdef frozenset _places

    cdef Clock _clock
    cdef SojournTimeCollector _collector

    cdef float _arrival_time       #: float = cython.declare(cython.float)

    cpdef report_construction(self)
    cpdef report_destruction(self)

    cpdef report_arrival_at(self, Place p)
    @cython.locals(current_time=cython.float, sojourn_time=cython.float)
    cpdef report_departure_from(self, Place p)


cdef class FiringCollector(GenericCollector):
    cdef array _transition     # unsigned long[]
    cdef array _firing_time    # double[]
    cdef array _interval       # double[]

    cdef collect(self, unsigned long transition, double firing_time, double interval)


cdef class TransitionIntervalPluginTransitionObserver:
    cdef object _plugin   # Plugins.Plugin
    cdef Transition _transition
    cdef Clock _clock
    cdef FiringCollector _collector
    cpdef float _previous_firing_time

    @cython.locals(current_time=cython.double, interval=cython.double)
    cpdef after_firing(self, )

    cpdef reset(self)


