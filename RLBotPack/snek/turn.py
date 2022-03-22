import math
from typing import Optional, List

from settings import VERTICAL_TURNS
from utilities.vec import Vec3


class Turn:
    def __init__(self, dir: Vec3, axis: Optional[Vec3]):
        self.dir = dir
        self.axis = axis

    @staticmethod
    def all(car) -> List['Turn']:
        halfpi = math.pi / 2
        return [
            Turn(car.forward, None),
            Turn(car.left, car.up * halfpi),
            Turn(-car.left, car.up * -halfpi)
        ] if not VERTICAL_TURNS else [
            Turn(car.forward, None),
            Turn(car.left, car.up * halfpi),
            Turn(-car.left, car.up * -halfpi),
            Turn(car.up * 0.25, car.left * -halfpi),
            Turn(-car.up, car.left * halfpi),
        ]

    @staticmethod
    def no_turn(car) -> 'Turn':
        return Turn(car.forward, None)
