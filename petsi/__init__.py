""" The main package for Petsi - a Petri net simulator for performance modelling.

.. rubric:: Package interface

.. autosummary
    :template: package_interface_class.rst
    :recursive:
    :toctree:

.. autodata:: Simulator

.. rubric:: Private modules

.. autosummary::
    :template: module_reference.rst
    :toctree:
    :recursive:

    petsi._structure
"""
from .util import export

from .Simulation import Simulator

export(Simulator)
