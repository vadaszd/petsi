from dataclasses import dataclass, field
from functools import singledispatchmethod, reduce
from typing import Union, Tuple, Optional

from ._structure import PetsiVisitor, Net, Transition, Place, Arc, TestArc, InhibitorArc
from graphviz import Digraph

@dataclass
class Visualizer(PetsiVisitor):

    figsize: Optional[Tuple[float, float]]
    dot: Digraph = field(default_factory=Digraph, init=False)

    @singledispatchmethod
    def visit(self, visitable: Union[Net, Transition, Place, Arc]):
        pass

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
