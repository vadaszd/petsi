import cython


cdef class Place



cdef class Transition:
    cdef readonly basestring _name   #= cython.declare(cython.basestring)
    cdef readonly int priority  #: int #= cython.declare(cython.int, visibility='readonly')
    cdef readonly float weight    # : float #= cython.declare(cython.float, visibility='readonly')
    cdef object _distribution  #: "Callable[[], float]"

    cdef int _disabled_arc_count   #: int = cython.declare(cython.int)
    cdef dict _arcs    # : "Dict[str, Arc]" = cython.declare(dict)
    cdef readonly set _transition_observers   #: "Set[Plugins.AbstractTransitionObserver]" = cython.declare(set, visibility="readonly")


    cdef float get_duration(self)

    @cython.locals(old_disabled_arc_count=int)
    cdef increment_disabled_arc_count(self)

    cdef decrement_disabled_arc_count(self)


cdef class Token:
    cdef object _typ            # : TokenType
    cdef set _token_observers   # : "Set[Plugins.AbstractTokenObserver]" = cython.declare(set)
    cdef dict tags              #: "Dict[str, Any]"

    cdef deposit_at(self, Place place)
    cdef remove_from(self, Place place)
    cdef delete(self)


cdef class Place:
    cdef basestring _name
    cdef object _typ  # :  TokenType
    cdef object _tokens  # : "Deque[Token]" # = cython.declare(_collections.deque)
    cdef readonly set _place_observers  #: "Set[Plugins.AbstractPlaceObserver]" = cython.declare(set, visibility="readonly")
    cdef readonly set _presence_observers  #: "Set[PresenceObserver]" = cython.declare(set, visibility="readonly")

    cdef readonly object _status    #: _Status = cython.declare(object, visibility="readonly")

    @cython.locals(token=Token, presence_observer=PresenceObserver,)
    cdef Token pop(self)

    @cython.locals(token=Token, presence_observer=PresenceObserver, was_empty=cython.bint)
    cdef push(self,  token )

    cdef bint _is_empty(self)

    cdef Token _pop(self)

    cdef _push(self, Token token)