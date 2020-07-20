from typing import TYPE_CHECKING

from .._meters import GenericCollector

if TYPE_CHECKING:
    from typing import Optional, FrozenSet

    # Need to rename Clock, otherwise it collides with the cimported Clock in the .pxd file!
    from ..autofire import Clock as TClock

    # Same trick for Token and Place
    from ..._structure import Token as TToken, Place as TPlace

    from ..interface import APlugin


class SojournTimeCollector(GenericCollector):
    """ Collect data about the visits of tokens at places when the visit is completed.

    For an overview see :ref:`collecting-simulation-data`.

    .. rubric:: Structure of the observations collected
    .. csv-table::
        :header:  Field name, Data type, Description
        :widths: auto

        ``token_id``, ``unsigned long long (64 bits)``, A unique number identifying the token
        ``token_type``, ``unsigned int (16 bits)``, The index of the token type.
        ``start_time``, ``double``, The time the token arrived at the place.
        ``visit_number``,``unsigned long long (64 bits)``, "The number of transitions the token suffered before arriving at the place."
        ``place`` ,``unsigned int (16 bits)``  , The index of the place in the places array.
        ``duration`` , ``double``, How long the token stayed at the place (sojourn time)

    """
    _type_codes = dict(token_id='Q',      # unsigned long long (64 bits)
                       token_type='I',    # unsigned int (16 bits)
                       start_time='d',    # double
                       visit_number='Q',  # unsigned long long (64 bits)
                       place='I',         # unsigned int (16 bits)
                       duration='d',      # double
                       )

    def reset(self):
        super().reset()
        # noinspection PyAttributeOutsideInit
        self._token_id, self._token_type, self._start_time, self._visit_number, self._place, self._duration = \
            self._arrays.values()

    # This would be the correct type-annotated signature, but cython crashes with argument annotations
    # def collect(self, token_id: int, token_type: int, start_time: float,
    #             visit_number: int, place: int, duration: float):
    def collect(self, token_id, token_type, start_time,
                visit_number, place, duration):
        self._token_id.append(token_id)
        self._token_type.append(token_type)
        self._start_time.append(start_time)
        self._visit_number.append(visit_number)
        self._place.append(place)
        self._duration.append(duration)


class SojournTimePluginTokenObserver:  # Cython does not cope with base classes here

    def __init__(self,
                 _plugin: "APlugin",
                 _token: "TToken",
                 _places: "Optional[FrozenSet[int]]",
                 _clock: "TClock",
                 _collector: SojournTimeCollector,
                 _token_id: int):
        self._plugin = _plugin
        self._token = _token
        self._token_id = _token_id
        self._visit_number = 0
        self._places = _places
        self._clock = _clock
        self._collector = _collector
        self._arrival_time = 0.0

    def reset(self):
        """ Do nothing.

        This method is called when all marking-related state is removed from the Petri net.
        This observer and the observed token will also be removed,
        so there is no need to change anything in the state of the observer.
        """

    def report_construction(self):
        """ Do nothing """

    def report_destruction(self):
        """ Do nothing """

    def report_arrival_at(self, _: "TPlace"):
        """ Start the time measurement for the visit at the place"""
        # if self._places is None or p.ordinal in self._places:
        self._arrival_time = self._clock.read()

    def report_departure_from(self, p: "TPlace"):
        """ Stop the time measurement and report the sojourn time.

            The s.t. is only reported if `p` is among the places of interest specified in the constructor.
        """
        if self._places is None or p.ordinal in self._places:
            current_time: float = self._clock.read()
            sojourn_time: float = current_time - self._arrival_time
            self._collector.collect(self._token_id, self._token.typ.ordinal, self._arrival_time,
                                    self._visit_number, p.ordinal, sojourn_time)

        self._visit_number += 1
