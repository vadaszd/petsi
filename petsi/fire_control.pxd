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
    cpdef float read(self)


cdef class FireControl:
    cdef readonly float current_time
    cdef public bint _is_build_in_progress

    cdef object _deadline_disambiguator      # : Iterator[int]  # = cython.declare(cython.iterator)
    cdef dict _transition_enabled_at_start_up  #: Dict["Structure.Transition", bool] = cython.declare(dict)
    cdef list _active_priority_levels          #: List[_PriorityLevel] = cython.declare(list)
    cdef set _active_priorities                #: Set[int] = cython.declare(set)
    cdef object _priority_levels          # : Dict[int, _PriorityLevel] = cython.declare(defaultdict)
    cdef list _timed_transitions               # : List[Tuple[float, int, "Structure.Transition"]] = cython.declare(list)

    cpdef enable_transition(self, Transition transition)
    cpdef disable_transition(self, Transition transition)

    @cython.locals(deadline=cython.float)
    cdef _schedule_timed_transition(self, Transition transition)

    cdef _remove_timed_transition_from_schedule(self, Transition transition)

    @cython.locals(priority=cython.int, priority_level=_PriorityLevel)
    cdef _enable_transition(self, Transition transition)

    @cython.locals(priority_level=_PriorityLevel)
    cdef _disable_transition(self, Transition transition)

    cdef Transition _next_timed_transition(self)

    @cython.locals(priority_level=_PriorityLevel, new_time=cython.float, weights=list, transition=Transition)
    cpdef tuple _select_next_transition(self)


cdef class SojournTimePluginTokenObserver:
    cdef object _plugin   # Plugins.Plugin
    cdef Token _token

    # A function returning the current time
    cdef Clock _clock

    # The overall sojourn time of the observed token for each visited place
    cdef object _overall_sojourn_time  # : DefaultDict[str, float]

    cdef float _arrival_time       #: float = cython.declare(cython.float)

    cpdef report_construction(self)
    cpdef report_destruction(self)

    cpdef report_arrival_at(self, Place p)
    @cython.locals(current_time=cython.float, sojourn_time=cython.float)
    cpdef report_departure_from(self, Place p)


cdef class TokenCounterPluginPlaceObserver:
    cdef object _plugin      #: Plugin
    cdef Place _place        #: "Structure.Place" = cython.declare("Structure.Place")

    cdef Clock _clock

    cdef int _num_tokens       #: int = cython.declare(cython.int)

    cdef float _time_of_last_token_move    # : float = cython.declare(cython.float)

    cdef list _time_having      # : List[float] = cython.declare(list)


    @cython.locals(now=cython.float, duration=cython.float)
    cdef _update_num_tokens_by(self, int delta)

    cpdef report_arrival_of(self, token)

    cpdef report_departure_of(self, token)



