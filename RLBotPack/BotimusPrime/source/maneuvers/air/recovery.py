from maneuvers.kit import *

from maneuvers.driving.arrive import Arrive

class Recovery(Maneuver):
    def __init__(self, car: Car):
        super().__init__(car)

        self.turn = AerialTurn(car)

    def step(self, dt):
        self.turn.step(dt)
        self.controls = self.turn.controls
        self.controls.throttle = 1
        self.finished = self.turn.finished or self.car.on_ground