import cython
from .Structure cimport Transition, Token, Place
from cpython cimport iterator

# from cpython cimport defaultdict

cdef class _PriorityLevel:
    cdef int priority
    cdef set transitions    #: Set["Structure.Transition"]

    cdef add(self, Transition transition)

    cdef remove(self, Transition transition)


cdef class Clock:
    cdef FireControl _fire_control
    cpdef double read(self) except -999


cdef class FireControl:
    cdef readonly double current_time
    cdef public bint _is_build_in_progress

    cdef object _deadline_disambiguator      # : Iterator[int]  # = cython.declare(cython.iterator)
    cdef dict _transition_enabled_at_start_up  #: Dict["Structure.Transition", bool] = cython.declare(dict)
    cdef list _active_priority_levels          #: List[_PriorityLevel] = cython.declare(list)
    cdef set _active_priorities                #: Set[int] = cython.declare(set)
    cdef object _priority_levels          # : Dict[int, _PriorityLevel] = cython.declare(defaultdict)
    cdef list _timed_transitions               # : List[Tuple[float, int, "Structure.Transition"]] = cython.declare(list)

    cpdef enable_transition(self, Transition transition)
    cpdef disable_transition(self, Transition transition)

    @cython.locals(deadline=cython.double)
    cdef _schedule_timed_transition(self, Transition transition)

    cdef _remove_timed_transition_from_schedule(self, Transition transition)

    @cython.locals(priority=cython.int, priority_level=_PriorityLevel)
    cdef _enable_transition(self, Transition transition)

    @cython.locals(priority_level=_PriorityLevel)
    cdef _disable_transition(self, Transition transition)

    cdef Transition _next_timed_transition(self)

    @cython.locals(priority_level=_PriorityLevel, new_time=cython.double, weights=list, transition=Transition)
    cpdef tuple _select_next_transition(self)


cdef class AutoFirePluginTransitionObserver:
    cdef object _plugin   # Plugins.Plugin
    cdef Transition _transition
    cdef FireControl _fire_control
    cdef double _deadline

    cpdef got_enabled(self, )
    cpdef got_disabled(self, )
    cpdef reset(self)
    cpdef after_firing(self)
    cpdef before_firing(self)


