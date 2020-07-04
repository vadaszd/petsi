from ..._structure cimport Transition
from ..autofire._autofire cimport Clock
from .._meters cimport GenericCollector
from cpython.array cimport array
import cython


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
    cpdef double _previous_firing_time

    cpdef got_enabled(self, )
    cpdef got_disabled(self, )
    cpdef reset(self)

    @cython.locals(current_time=cython.double, interval=cython.double)
    cpdef after_firing(self, )

    cpdef before_firing(self)


