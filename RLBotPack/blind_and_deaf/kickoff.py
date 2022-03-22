from math import atan2

from rlutilities.simulation import Game, Input, Car
from rlutilities.linear_algebra import vec3, dot
from rlutilities.mechanics import Drive


class Kickoff:
    def __init__(self, car: Car, info: Game):
        self.car: Car = car
        self.info: Game = info
        self.controls = Input()
        self.drive = Drive(car)

    def step(self, dt):
        self.drive.target = self.info.ball.position
        self.drive.speed = 1500
        self.drive.step(self.info.time_delta)
        self.controls = self.drive.controls
