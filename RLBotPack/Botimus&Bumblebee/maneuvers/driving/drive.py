import math

from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, dot, normalize
from tools.arena import Arena
from tools.drawing import DrawingTool
from tools.math import abs_clamp, clamp11, clamp
from tools.vector_math import ground, local, ground_distance, distance, direction


class Drive(Maneuver):

    def __init__(self, car, target_pos: vec3 = vec3(0, 0, 0), target_speed: float = 0, backwards: bool = False):
        super().__init__(car)

        self.target_pos = target_pos
        self.target_speed = target_speed
        self.backwards = backwards
        self.drive_on_walls = False

    def step(self, dt):
        target = self.target_pos

        # don't try driving outside the arena
        target = Arena.clamp(target, 100)

        # smoothly escape goal
        if abs(self.car.position[1]) > Arena.size[1] - 50 and abs(self.car.position.x) < 1000:
            target = Arena.clamp(target, 200)
            target[0] = abs_clamp(target[0], 700)

        if not self.drive_on_walls:
            seam_radius = 100 if abs(self.car.position[1]) > Arena.size[1] - 100 else 200
            if self.car.position[2] > seam_radius:
                target = ground(self.car)

        local_target = local(self.car, target)

        if self.backwards:
            local_target[0] *= -1
            local_target[1] *= -1

        # steering
        phi = math.atan2(local_target[1], local_target[0])
        self.controls.steer = clamp11(2.5 * phi)

        # powersliding
        self.controls.handbrake = 0
        if (
                abs(phi) > 1.5
                and self.car.position[2] < 300
                and (ground_distance(self.car, target) < 3500 or abs(self.car.position[0]) > 3500)
                and dot(normalize(self.car.velocity), self.car.forward()) > 0.85
        ):
            self.controls.handbrake = 1

        # forward velocity
        vf = dot(self.car.velocity, self.car.forward())
        if self.backwards:
            vf *= -1

        # speed controller
        if vf < self.target_speed:
            self.controls.throttle = 1.0
            if self.target_speed > 1400 and vf < 2250 and self.target_speed - vf > 50:
                self.controls.boost = 1
            else:
                self.controls.boost = 0
        else:
            if (vf - self.target_speed) > 400:  # 75
                self.controls.throttle = -1.0
            elif (vf - self.target_speed) > 100:
                if self.car.up()[2] > 0.85:
                    self.controls.throttle = 0.0
                else:
                    self.controls.throttle = 0.01
            self.controls.boost = 0

        # backwards driving
        if self.backwards:
            self.controls.throttle *= -1
            self.controls.steer *= -1
            self.controls.boost = 0
            self.controls.handbrake = 0

        # don't boost if not facing target
        if abs(phi) > 0.3:
            self.controls.boost = 0

        # finish when close
        if distance(self.car, self.target_pos) < 100:
            self.finished = True

    @staticmethod
    def turn_radius(speed: float) -> float:
        spd = clamp(speed, 0, 2300)
        return 156 + 0.1 * spd + 0.000069 * spd ** 2 + 0.000000164 * spd ** 3 + -5.62E-11 * spd ** 4

    def render(self, draw: DrawingTool):
        draw.color(draw.cyan)
        draw.square(self.target_pos, 50)

        target_direction = direction(self.car.position, self.target_pos)
        draw.triangle(self.car.position + target_direction * 200, target_direction, up=self.car.up())
