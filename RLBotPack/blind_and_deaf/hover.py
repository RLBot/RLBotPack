from rlutilities.simulation import Game, Input, Car
from rlutilities.linear_algebra import vec3, look_at, norm
from rlutilities.mechanics import AerialTurn


def normalized(v):
    return v / norm(v)

def direction(a, b):
    return normalized(b - a)


class Hover:
    def __init__(self, car: Car, info: Game):
        self.turn = AerialTurn(car)

        self.target = None
        self.car: Car = car
        self.info: Game = info
        self.controls = Input()
        self.jump = False

    def step(self, dt):
        delta_target = self.target - self.car.position

        if norm(delta_target) > 500:
            delta_target = direction(self.car.position, self.target) * 500

        target_direction = delta_target - self.car.velocity + vec3(0, 0, 500)

        self.turn.target = look_at(target_direction, direction(self.car.position, vec3(0, 0, 0)))
        self.turn.step(dt)
        self.controls = self.turn.controls
        self.controls.boost = delta_target[2] - self.car.velocity[2] * 0.5 > 0 and self.car.forward()[2] > 0.2
        self.controls.throttle = not self.car.on_ground
        self.controls.jump = 25 < self.car.position[2] < 80 or self.car.on_ground