Why `PetSi`?
======================

`PetSi` is a stochastic `Petri net Simulator` for performance modelling of distributed systems.

`PetSi` can imitate streams of performance metrics coming from a stateful,
`concurrent <https://en.wikipedia.org/wiki/Concurrent_computing>`_,
`non-deterministic <https://en.wikipedia.org/wiki/Indeterminacy_in_concurrent_computation>`_ system.
What exactly it can emulate is described in :doc:`Semantics`.

Being able to evaluate different system architectures without actually having to first implement them
or assessing the effects of performance tuning adjustments before deploying them to a sensitive
production environment are of interest to a wide audience including architects, system designers, developers and
performance analysts. And these days distributed systems cover not only cloud applications but also traditional ones,
as the internals of modern computers increasingly resemble computer networks.

`Petri nets <https://en.wikipedia.org/wiki/Petri_net>`_ were an active research topic in the decades around 2000 (see e.g.
`search trends <https://trends.google.com/trends/explore?date=all&q=petri%20net>`_ for the term).
During the decade a number of implementations have been developed. The goal of these implementations were
exploration and education, which resulted in a *huge diversity even at the conceptual level*,
at the expense of the practical usability of these tools in an industry setting.

For an overview the interested reader can refer to the
`Petri net tool database <https://www.informatik.uni-hamburg.de/TGI/PetriNets/tools/>`_
of the University of Hamburg or one of the numerous review papers like
`A Survey of Petri Net Tools <https://www.researchgate.net/publication/282209737_A_Survey_of_Petri_Net_Tools>`_.

Unfortunately most of these tools

- are *outdated* to the extent that one cannot easily run them
- *do not fit into a modern analytical software environment* like a Jupyter notebook
- are *no longer maintained*
- are *not free for industrial use*

These factors have become blockers for Petri nets becoming an industry practice and limited their popularity to the
academic realm.

`PetSi` is trying to address these problems and demonstrate the practical usability of Petri nets for the
performance modelling of distributed computer systems.
That is, `PetSi` focuses on one particular area of Petri net applications and does not pretend to be a
general purpose tool. It follows the `Unix philosophy <https://en.wikipedia.org/wiki/Unix_philosophy>`_:

.. highlights::

   *Do one thing and do it well.*

For PetSi, that one thing is performance modelling of distributed computer systems,
as opposed to excelling as a Petri net research tool.

Why simulation?
------------------------------
Petri nets can be mathematically "solved" as a system of linear equations under certain conditions, such as

- The number of reachable markings must be finite
- The time gaps between subsequent firings of transitions must ne statistically independent
  (i.e. firing times must be exponentially distributed)

In the practice of performance modeling the exact numerical solution is rarely viable:

- The condition related to the firing times is rarely met
- Even if the number of markings is finite, it tends to be a large number, resulting in a sizable number of equations
- If the mean time of firings vary on a large scale, the solution can be numerically unstable due to the poor
  conditioning of the system of equations.

Therefore, in its current version `PetSi` comes with approximation solutions only,
based on simulations implemented in a built-in plugin.

However, this does not preclude featuring a precise numerical solution at a later stage,
implemented using one of `PetSi`'s :ref:`extension mechanisms <extension-mechanisms>`.