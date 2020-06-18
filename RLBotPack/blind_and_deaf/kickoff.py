from math import atan2

from rlutilities.simulation import Game, Input, Car
from rlutilities.linear_algebra import vec3, dot


def local(car: Car, pos: vec3) -> vec3:
    return dot(pos - car.position, car.orientation)

def clamp(x, a, b):
    """clamp x to range [a, b]"""
    return max(a, min(x, b))


class Kickoff:
    def __init__(self, car: Car, info: Game):
        self.car: Car = car
        self.info: Game = info
        self.controls = Input()

    def step(self, dt):
        car_to_ball = local(self.car, self.info.ball.position)
        angle = atan2(car_to_ball[1], car_to_ball[0])

        self.controls.throttle = 1.0
        self.controls.handbrake = abs(angle) > 1.5
        self.controls.steer = clamp(angle**3, -1.0, 1.0)
