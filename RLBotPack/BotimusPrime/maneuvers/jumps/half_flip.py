import math
from math import sqrt

from rlutilities.linear_algebra import vec2, vec3, mat3, norm, normalize, look_at, angle_between, clip, cross, dot, sgn, xy, axis_to_rotation, rotation_to_axis, transpose
from rlutilities.simulation import Car, Input
from rlutilities.mechanics import Dodge

class HalfFlip:

    def __init__(self, car: Car, use_boost=False):
        self.car = car
        self.use_boost = use_boost
        self.controls = Input()

        self.dodge = Dodge(car)
        self.dodge.duration = 0.12
        self.dodge.direction = vec2(car.forward() * (-1))

        self.s = 0.95 * sgn(dot(self.car.angular_velocity, self.car.up()) + 0.01)

        self.timer = 0.0

        self.finished = False

    def step(self, dt):

        boost_delay = 0.4
        stall_start = 0.50
        stall_end = 0.70
        timeout = 2.0

        self.dodge.step(dt)
        self.controls = self.dodge.controls

        if stall_start < self.timer < stall_end:
            self.controls.roll = 0.0
            self.controls.pitch = -1.0
            self.controls.yaw = 0.0

        if self.timer > stall_end:
            self.controls.roll = self.s
            self.controls.pitch = -1.0
            self.controls.yaw = self.s

        if self.use_boost and self.timer > boost_delay:
            self.controls.boost = 1
        else:
            self.controls.boost = 0

        self.timer += dt

        self.finished = (self.timer > timeout) or \
                        (self.car.on_ground and self.timer > 0.5)
