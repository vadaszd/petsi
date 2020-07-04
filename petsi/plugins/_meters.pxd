# This file is needed because GenericCollector is a base class for extension classes.

from cpython.array cimport array

cdef class GenericCollector:
    cdef public int required_observations
    cdef dict _arrays      #: Dict[str, array]
    cdef array _any_array

    # def reset(self)
    # cpdef get_observations(self) -> Dict[str, array]
    # def need_more_observations(self) -> bool:

