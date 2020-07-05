""" A Petri net visitor that generates a `graphviz` representation of the net.

.. figure:: ../Simple Loopback Petri Net.png
    :alt: A simple Petri net

    The generated `graphviz` representation of a simple example Petri net.

"""

from dataclasses import dataclass, field
from functools import singledispatchmethod, reduce
from typing import Union, Tuple, Optional
from graphviz import Digraph

from .Visitor import PetsiVisitor
from ._structure import Net, Transition, Place, Arc, TestArc, InhibitorArc


@dataclass
class Visualizer(PetsiVisitor):
    """ A Petri net visitor converting the net to a :class:`~graphviz.Digraph` object.

    """
    figsize: Optional[Tuple[float, float]]
    dot: Digraph = field(default_factory=Digraph, init=False)

    @singledispatchmethod
    def visit(self, visitable: Union[Net, Transition, Place, Arc]):
        """ A generic ``visit`` method.

        The implementation uses the :class:`~functools.singledispatchmethod` for dispatching
        control based on the type of the visited object.

        `Transitions <petsi._structure.Transition>`_ are represented by a box-shaped `graphviz` node.
        Timed transitions have rounded corners.
        Oval nodes represent `places <petsi._structure.Place>`_.

        Arcs are shown as edges between places and transitions.
        Edges normally have an arrow shaped head pointing into the direction of token flow.
        Transfer arcs are represented by two edges, one from the input place to the transition
        and another from the transition to the output place.
        An edge without arrowhead indicates a test arc. A dot arrowhead turns the test arc into an inhibitor.
        """

    @visit.register
    def _(self, visitable: Net):
        self.dot = Digraph(name=visitable.name,
                           engine='neato',
                           graph_attr=dict(overlap='false',
                                           size='' if self.figsize is None else f'{self.figsize[0]}, {self.figsize[1]}!',
                                           ratio='fill',
                                           # concentrate='true',
                                           ),
                           node_attr=dict(fontsize='10',
                                          width='0.05',
                                          height='0.05',
                                          margin='0.05'),
                           edge_attr=dict(arrowhead='vee',
                                          arrowsize='0.75',
                                          fontsize='7',
                                          ),
                           )

    @visit.register
    def _(self, visitable: Transition):
        escaped_name = reduce(lambda s, pattern: s.replace(*pattern),
                              (('{', r'\{'), ('{', r'\{'), ('|', r'\|')),
                              visitable.name
                              )
        attributes = dict(shape='box')

        if visitable.is_timed:
            attributes.update(style='rounded,dashed', )
        else:
            attributes.update(label=f'{escaped_name}\nw={visitable.weight:4.2f}', )

        self.dot.node(visitable.name, **attributes)

    @visit.register
    def _(self, visitable: Place):
        self.dot.node(visitable.name, shape='oval', margin='0.0')

    @visit.register
    def _(self, visitable: Arc):
        try:
            input_place = visitable.input_place
        except AttributeError:
            pass
        else:
            self.dot.edge(input_place.name, visitable.transition.name, label=visitable.name,
                          len=('0.5' if visitable.transition.is_timed else '1.0'), dir='1',
                          )

        try:
            output_place = visitable.output_place
        except AttributeError:
            pass
        else:
            self.dot.edge(visitable.transition.name, output_place.name, label=visitable.name,
                          len=('0.5' if visitable.transition.is_timed else '1.0'), dir='1',
                          )

    @visit.register
    def _(self, visitable: TestArc):
        input_place = visitable.input_place
        self.dot.edge(input_place.name, visitable.transition.name,
                      label=visitable.name, arrowhead='none', style='dashed')

    @visit.register
    def _(self, visitable: InhibitorArc):
        input_place = visitable.input_place
        self.dot.edge(input_place.name, visitable.transition.name,
                      label=visitable.name, arrowhead='dot', style='dashed')
