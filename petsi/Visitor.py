""" The visitor interface for Petri nets.

Visitors can be used to transform the Petri nets into alternate representations or manipulate them in other ways.

An example implementation of the visitor interface is :class:`petsi.NetViz.Visualizer`.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from ._structure import Net, Transition, Place, Arc
    from typing import Union

APetsiVisitor = TypeVar('APetsiVisitor', bound="PetsiVisitor")


class PetsiVisitor(ABC):
    """ Abstract base class for Petri net visitors."""
    @abstractmethod
    def visit(self, visitable: "Union[Net, Transition, Place, Arc]"):
        """ Visit an element of the Petri net and generate an alternate represention for it."""
