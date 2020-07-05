""" The main package for Petsi - a Petri net simulator for performance modelling.

.. rubric:: Synopsis

.. code-block:: python

    from petsi import Simulator
    simulator = Simulator(...)

.. autodata:: Simulator

    For the interface documentation, refer to :class:`.Simulation.Simulator`.

.. rubric:: Internal submodules

.. autosummary::
    :template: module_reference.rst
    :toctree:
    :recursive:

    petsi._structure
"""
from .util import export

from .Simulation import Simulator

export(Simulator)
