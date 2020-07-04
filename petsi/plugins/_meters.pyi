from array import array
from typing import Dict


class GenericCollector:
    required_observations: int
    _type_codes: Dict[str, str]
    _arrays: Dict[str, array]
    _any_array: array

    def __init__(self, required_observations: int): pass

    def reset(self): pass

    def get_observations(self) -> Dict[str, array]:
        pass

    def need_more_observations(self) -> bool: pass

