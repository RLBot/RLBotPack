from typing import Optional

from maneuvers.jumps.jump import Jump
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, dot, normalize, sgn

# Most of this class is from the old RLUtilities, made by chip.
# The dodge in the new RLUtilities is a bit different, and my shot mechanics are tuned for this one, so I kept it.
from tools.math import clamp11


class AirDodge(Maneuver):
    """
    Dodge towards a target position. If target is None, do a double jump.
    """
    def __init__(self, car, jump_duration=0.0, target=None):
        super().__init__(car)
        self.target: Optional[vec3] = target

        self.jump = Jump(jump_duration)

        if jump_duration <= 0:
            self.jump.finished = True

        self.counter = 0
        self.state_timer = 0.0
        self.total_timer = 0.0

    def interruptible(self) -> bool:
        return False

    def step(self, dt):

        recovery_time = 0.0 if (self.target is None) else 0.4

        if not self.jump.finished:

            self.jump.step(dt)
            self.controls = self.jump.controls

        else:

            if self.counter == 0:

                # double jump
                if self.target is None:
                    self.controls.roll = 0
                    self.controls.pitch = 0
                    self.controls.yaw = 0

                # air dodge
                else:
                    target_local = dot(self.target - self.car.position, self.car.orientation)
                    target_local[2] = 0

                    target_direction = normalize(target_local)

                    self.controls.roll = 0
                    self.controls.pitch = -target_direction[0]
                    self.controls.yaw = clamp11(sgn(self.car.orientation[2, 2]) * target_direction[1])

                    if target_local[0] > 0 and dot(self.car.velocity, self.car.forward()) > 500:
                        self.controls.pitch = self.controls.pitch * 0.8
                        self.controls.yaw = clamp11(self.controls.yaw * 5)

            elif self.counter == 2:

                self.controls.jump = 1

            elif self.counter >= 4:

                self.controls.roll = 0
                self.controls.pitch = 0
                self.controls.yaw = 0
                self.controls.jump = 0

            self.counter += 1
            self.state_timer += dt

        self.finished = self.jump.finished and self.state_timer > recovery_time and self.counter >= 6
