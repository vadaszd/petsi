""" A Cython extension module providing a generic data collector.
"""

from array import array
from typing import Dict


class GenericCollector:
    """ A generic data collector for collecting statistics about the activities in the Petri net.

    .. note:: This is an abstract class with incomplete functionality.

              We cannot derive it from :class:`abc.ABC` as Cython does not support ABCs.

    The collector is acting as a typed buffer of rows, each row consisting of named and typed fields.
    Data is added row-by-row with the :meth:`collect` method (which must be defined in sub-classes)
    but retrieved column-oriented with the :meth:`get_observations` method, as a dictionary of
    :class:`arrays <array.array>`.

    Derived classes must also define a :attr:`_type_codes` class or instance attribute.
    The attribute must be a dictionary. Its keys and values will be used as the keys and :data:`array.type_codes` in
    the dictionary returned by :meth:`get_observations` and in :attr:`_arrays`.

    .. method:: collect(self, ...)
        :abstractmethod:

        This method is a placeholder for code to populate :attr:`_arrays`.
        For performance, it is recommended to define it as ``cdef`` in Cython, for example:

        ``cdef collect(self, unsigned long foo, double bar)``

        The implementer of the derived class is free to choose the signature of the method
        (in fact the name could also at his/her discretion.)

    .. attribute:: _type_codes
        :type: Dict[str, str]

        A class or instance attribute. Its keys define the name, while the values determine
        the type of the fields in the observations collected in :attr:`_arrays`.
        The values must be chosen from :data:`array.type_codes`

    .. attribute:: _arrays
        :type: Dict[str, array.array]

        Every time the :meth:`collect` method is invoked it should add the same number of observations
        to each of these arrays.
    """

    def __init__(self, required_observations: int):
        """ Initialize the collector via :meth:`reset`.

        :param required_observations: The number of observations to accumulate in :attr:`_arrays` before
                :meth:`need_more_observations` returns ``False``
        """
        self.required_observations = required_observations
        self._arrays = dict()
        self.reset()

    def reset(self):
        """ Place newly created, empty arrays into :attr:`_arrays`

        In derived classes this mthod can be extended to initialize custom instance attributes to point at
        the arrays, so that :meth:`collect` can bypass the lookup operation on :attr:`_arrays`
        """
        self._arrays.clear()
        self._arrays.update((field_name, array(type_code)) for field_name, type_code in self._type_codes.items())
        # noinspection PyAttributeOutsideInit
        self._any_array = next(iter(self._arrays.values()))    # for calculating the number of observations

    def get_observations(self) -> Dict[str, array]:
        """ Retrieve the collected observations.

        This method implicitly :meth:`resets <reset>` the state of the collector.
        """
        data = self._arrays.copy()
        self.reset()
        return data

    def need_more_observations(self) -> bool:
        """ Determine if we have collected enough data.

        :return: ``False`` if at least ``required_observations`` have been collected since
                 the last call to :meth:`get_observations`
        """
        return len(self._any_array) < self.required_observations

