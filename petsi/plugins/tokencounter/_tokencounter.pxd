from ..._structure cimport Place
from ..autofire._autofire cimport Clock
from .._meters cimport GenericCollector
from cpython.array cimport array
import cython


cdef class TokenCounterCollector(GenericCollector):
    cdef array _start_time
    cdef array _place
    cdef array _count
    cdef array _duration

    cdef collect(self, double start_time, unsigned int place, unsigned long long count, double duration)


cdef class TokenCounterPluginPlaceObserver:
    cdef object _plugin      #: Plugin
    cdef Place _place        #: "_structure.Place" = cython.declare("_structure.Place")
    cdef Clock _clock
    cdef TokenCounterCollector _collector

    cdef int _num_tokens       #: int = cython.declare(cython.int)

    cdef double _time_of_last_token_move    # : float = cython.declare(cython.double)

    cdef list _time_having      # : List[float] = cython.declare(list)


    @cython.locals(now=cython.double, duration=cython.double)
    cdef _update_num_tokens_by(self, int delta)

    cpdef report_arrival_of(self, token)

    cpdef report_departure_of(self, token)


