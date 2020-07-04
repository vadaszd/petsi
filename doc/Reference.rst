API Reference
=================

The Petsi API consists of multiple parts. Follow the links below to the documentations of the modules
that define the APIs. Some other links lead to examples on how to use these interfaces:

- The :doc:`simulation API <_generated/petsi.Simulation>` is of interest if you want to create Petri nets and
  run performance simulations.

- The :doc:`plugin API <_generated/petsi.plugins.Plugins>` is for extending Petsi with additional functionality based
  on the `observer pattern <https://en.wikipedia.org/wiki/Observer_pattern>`_. Even Petsi uses this interface
  to implement some of its built-in functionality like automatically selecting and
  :doc:`firing transitions <_generated/petsi.plugins.autofire>`
  and :doc:`collecting metrics <_generated/petsi.plugins.meters>` about the places, transitions or tokens of the net.

- The :doc:`visitor API <_generated/petsi.Visitor>` allows for transforming the Petri net into alternate
  representations. An example of this is the :doc:`NetViz <_generated/petsi.NetViz>` module visualizing
  the net with :mod:`graphviz`.

