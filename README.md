# A Petri net simulator for performance modelling 

### Example
```python
import petsi
from random import uniform
from typing import Dict, Tuple, Callable


def create_simulator(initial_work: int, utilization: float, firing_distribution: Callable[[], float], **loop_backs: Dict[str, Tuple[int, int]]):
    # print(f"    Initial work:{initial_work}, utilization={utilization}")
    simulator = petsi.Simulator("Activity time")
    simulator.add_place("ToDo")
    simulator.add_place("Done")

    simulator.add_immediate_transition("start", priority=1)
    simulator.add_inhibitor("is idle", "ToDo", "start")
    for i in range(initial_work):
        simulator.add_constructor(f"initial token #{i}", "start", "ToDo")

    simulator.add_timed_transition("doing", firing_distribution)
    simulator.add_transfer("do", "ToDo", "doing", "Done")

    constructor_weights = 0
    for transition_name, (multiplier, weight) in loop_backs.items():
        if multiplier > 0 and weight > 0:
            # print(f"      {transition_name} multiplier={multiplier}, weight={weight}")
            simulator.add_immediate_transition(transition_name, priority=2, weight=weight)
            simulator.add_transfer(f"{transition_name}", "Done", transition_name, "ToDo")
            for i in range(multiplier-1):
                constructor_weights += weight
                constructor_name = f"more-to-do #{i+1}"
                simulator.add_constructor(constructor_name, transition_name, "ToDo")

    destructor_weight = max(1.0, constructor_weights) / utilization
    simulator.add_immediate_transition("vanish", priority=2, weight=destructor_weight)
    simulator.add_destructor("end", "Done", "vanish")
    
    return simulator


simulator = create_simulator(1, utilization=0.75, 
                             firing_distribution=lambda: uniform(0, 0),
                             # 1 loop-back branch with weight 200
                             repeat=(1, 200), 
                             )


from IPython.display import display
display(simulator.show())

# Specify that we need 10000 observations of the firing of the 'start' transition 
get_transition_observations, = simulator.observe(transition_firing=10000, transitions=['start'])

# Make the observations
simulator.simulate()

# Read out the observations as a dictionary of python arrays
transition_observations = get_transition_observations()
```
