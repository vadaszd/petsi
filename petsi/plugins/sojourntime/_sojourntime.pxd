from ..._structure cimport Token, Place
from ..autofire._autofire cimport Clock
from .._meters cimport GenericCollector
from cpython.array cimport array
import cython


cdef class SojournTimeCollector(GenericCollector):
    cdef array _token_id
    cdef array _token_type
    cdef array _start_time
    cdef array _visit_number
    cdef array _place
    cdef array _duration

    cdef collect(self, unsigned long long token_id,
                       unsigned int token_type,
                       double start_time,
                       unsigned long long visit_number,
                       unsigned int place, double duration)


cdef class SojournTimePluginTokenObserver:
    cdef object _plugin   # Plugins.Plugin
    cdef Token _token
    cdef unsigned long long _token_id
    cdef unsigned long long _visit_number
    cdef frozenset _places

    cdef Clock _clock
    cdef SojournTimeCollector _collector

    cdef double _arrival_time       #: double = cython.declare(cython.double)

    cpdef report_construction(self)
    cpdef report_destruction(self)

    cpdef report_arrival_at(self, Place p)
    @cython.locals(current_time=cython.double, sojourn_time=cython.double)
    cpdef report_departure_from(self, Place p)


