from rlutilities.simulation import Input, Car
from tools.drawing import DrawingTool


class Maneuver:
    def __init__(self, car):
        self.car: Car = car
        self.controls: Input = Input()
        self.finished: bool = False

    def step(self, dt: float):
        pass

    def interruptible(self) -> bool:
        return True

    def render(self, draw: DrawingTool):
        pass
