Supported Petri net semantics
======================================

.. rubric:: Overview

This page defines the flavour of Petri nets implemented in `PetSi` and provides high level guidelines on mapping
the defined elements to the concepts of distributed systems. For a more general introduction
refer to the Wikipedia article on Petri nets

A Petri net is a directed `bipartite graph <https://en.wikipedia.org/wiki/Bipartite_graph>`_,
on which a flow of tokens is interpreted. A node represents either a transition or
a place. Tokens flow along the directed edges called arcs, each of which
connects a place to a transition or a transition to a place.
The flow of the tokens happens in discrete, atomic steps when a transition fires
and is restricted to the arcs the transition is connected to. Between firings the tokens are stored
at the places. When the flow occurs, arcs perform some action on the flown tokens.
Atomicity means that either all or none of the arcs complete their flow actions. The transitions fire sequentially,
one after the other.

.. rubric:: Arcs

Based on their flow actions, we differentiate the following arc kinds:

- :class:`Presence observers <petsi._structure.PresenceObserver>` connect an *input place* to a transition.
  These kinds of arcs are sensitive to the presence or absence of a token at their input places and will prevent
  the transition from firing if the required conditions are not met.

  - :class:`Test arcs <TestArc>` require the presence of a token at their inputs but do not move any tokens.
  - :class:`Inhibitor arcs <InhibitorArc>` require the absence of any tokens at their inputs.
  - :class:`Destructor arcs <DestructorArc>` require the presence of a token and will destroy the selected token.
  - `Input arcs` [#ref3]_ require the presence of a token and
    cooperate with output arcs to move the selected token to another place.

- `Token placers` connect a transition to an *output place*.
  These arcs will place a token at that place as part of the transition firing.

  - :class:`Constructor arcs <ConstructorArc>` create a new token and place it at their output.
  - `Output arcs` [#ref3]_ move a token selected by their input halves to the output place.

.. rubric:: Transitions

At any moment of time, a transition is either:

- **Disabled**, meaning that at least one of its presence observer arcs prevent it from firing (by
  not being able to  carry out the flow actions [#ref4]_ ) or
- **Enabled**, meaning all arcs (including the presence observers) are able to carry out the flow actions.

Furthermore, transitions can be created to be *immediate* or *timed*. Immediate transitions are characterised by
their (positive integer) *priority* and (positive real) *weight*, timed transitions feature a continuous
*inter-firing-time probability distribution*, from which it is possible to draw *samples*. Timed transitions have
priority zero, i.e. lower than any immediate transition.

.. _firing-rules:

.. rubric:: Firing rules

`PetSi` comes with the capability of automatically selecting and firing transitions. This process obeys the following
rules:

#) Petri nets maintain a notion of continuous time *Petri net time*.
   The time of the net is initialized when the net is created.
   We may also refer to this quantity as *simulation time*.
#) Only enabled transitions are fired.
#) A transition cannot be fired if there is another enabled transition with a higher priority.
#) Ties among multiple enabled immediate transitions on the same priority level are resolved by selecting one
   randomly, with probability proportional to the weight of the competing transitions.
#) When a timed transition becomes enabled, its firing deadline is computed as the current simulation time
   plus a sample taken from its firing distribution.
#) Some :ref:`restrictions <place-restrictions>` on the structure of the net guarantee
   that once a timed transition is enabled, the only way to disable it is to fire it.
#) If no immediate transition is enabled, then the timed transition with the lowest deadline is fired
   and the simulation time is updated to the deadline of the fired transition.

.. rubric:: Token types

In `PetSi` tokens have an identity and a type. The identity allows for interpreting a history of the token's life.

.. rubric:: Places

Each place is associated with a token type specified when the place is created and is allowed to contain only
tokens of that type. Transitively the type of the place determines the type of tokens the arcs connected to the place
are going to act on.

If multiple tokens are present at a place, a decision needs to be made about which token will be flown by the next
action of the connected presence observer arcs. Based on the policy applied, `PetSi` differentiates

- :class:`FIFO places <petsi._structure.FIFOPlace>` and
- :class:`LIFO places <petsi._structure.FIFOPlace>`

.. _place-restrictions:
.. rubric:: Structural restrictions

The :ref:`firing rules <firing-rules>` above require that once a timed transition is enabled, the only way
to disable it is to fire it. `PetSi` enforces this by not allowing connections via presence observer arcs
between timed transitions and places with multiple token consumer arcs. The actual mechanism used is best explained
as a simple state machine:


#. When a place is created during the construction of the Petri net, it is in the ``UNDEFINED`` status.
#. When a token consumer arc is connected to the place, it enters the ``STABLE`` status.

XXXX


.. rubric:: Footnotes and references

.. [#ref1] https://en.wikipedia.org/wiki/Petri_net
.. [#ref2] http://pdv.cs.tu-berlin.de/PMFE-SS2007/StochasticPetriNets.pdf
.. [#ref3] Input and output arcs are implemented in a single :class:`~petsi._structure.TransferArc` class.
.. [#ref4] Arcs that are *not* presence observers are always able to carry out their flow actions.



transition (i.e. an event that may occur)
place (i.e. the state of fulfilling a condition)