from rlutilities.simulation import Game, Input, Car
from rlutilities.linear_algebra import vec3, normalize, look_at, norm
from rlutilities.mechanics import Reorient



class Hover:
    """
    PD controller for hovering in the air.
    This was also used in the Airshow :)
    """
    P = 2.8
    D = 3.0

    def __init__(self, car: Car):
        self.turn = Reorient(car)
        self.target: vec3 = None
        self.car: Car = car
        self.up: vec3 = None
        self.controls: Input = Input()
        self.__time_spent_on_ground = 0.0

    def step(self, dt):
        delta_target = self.target - self.car.position
        if norm(delta_target) > 700:
            delta_target *= 700 / norm(delta_target)

        target_direction = normalize(vec3(
            (delta_target[0]) * self.P - self.car.velocity[0] * self.D,
            (delta_target[1]) * self.P - self.car.velocity[1] * self.D,
            1000
        ))

        self.turn.target_orientation = look_at(target_direction, self.up)

        self.turn.step(dt)
        self.controls = self.turn.controls
        self.controls.boost = 0

        # tap boost to keep height
        if (delta_target[2] - self.car.velocity[2] * 0.5) > 0:
            self.controls.boost = 1
        # if the target is relatively far, hold boost even when we're higher than the target to keep moving
        if delta_target[2] < 0 and self.car.forward()[2] < 0.5:
            self.controls.boost = 1

        self.controls.throttle = True
