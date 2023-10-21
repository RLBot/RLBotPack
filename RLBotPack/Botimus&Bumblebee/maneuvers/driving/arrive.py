from typing import Optional

from maneuvers.driving.drive import Drive
from maneuvers.driving.travel import Travel
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, norm, normalize
from rlutilities.simulation import Car
from tools.drawing import DrawingTool
from tools.math import clamp, nonzero
from tools.vector_math import ground_distance, angle_to


class Arrive(Maneuver):
    """
    Arrive at a target position at a certain time (game seconds).
    You can also specify `target_direction`, and it will try to arrive
    at an angle. However this does work well only if the car is already
    roughly facing the specified direction, and only if it's far enough.
    """

    def __init__(self, car: Car):
        super().__init__(car)
        self.drive = Drive(car)
        self.travel = Travel(car)
        self.travel.drive.backwards = False
        self.action = self.drive

        self.target_direction: Optional[None] = None
        self.target: vec3 = None
        self.arrival_time: float = 0
        self.backwards: bool = False

        self.lerp_t = 0.56
        self.allow_dodges_and_wavedashes: bool = True
        self.additional_shift = 0
        self.asap = False

    def interruptible(self) -> bool:
        return self.action.interruptible()

    def step(self, dt):
        target = self.target
        car = self.car

        if self.target_direction is not None:
            car_speed = norm(car.velocity)
            target_direction = normalize(self.target_direction)

            # in order to arrive in a direction, we need to shift the target in the opposite direction
            # the magnitude of the shift is based on how far are we from the target
            shift = clamp(ground_distance(car.position, target) * self.lerp_t, 0, clamp(car_speed, 1500, 2300) * 1.6)

            # if we're too close to the target, aim for the actual target so we don't miss it
            if shift - self.additional_shift * 0.5 < Drive.turn_radius(clamp(car_speed, 500, 2300)) * 1.1:
                shift = 0
            else:
                shift += self.additional_shift

            shifted_target = target - target_direction * shift

            time_shift = ground_distance(shifted_target, target) / clamp(car_speed, 500, 2300) * 1.2
            shifted_arrival_time = self.arrival_time - time_shift

        else:
            shifted_target = target
            shifted_arrival_time = self.arrival_time

        self.drive.target_pos = shifted_target
        self.travel.target = shifted_target

        dist_to_target = ground_distance(car.position, shifted_target)
        time_left = nonzero(shifted_arrival_time - car.time)
        target_speed = clamp(dist_to_target / time_left, 0, 2300)

        if target_speed < 800 and dist_to_target > 1000 and angle_to(self.car, shifted_target) < 0.1:
            target_speed = 0

        # if self.asap:
        #     target_speed += 50

        self.drive.target_speed = target_speed
        self.drive.backwards = self.backwards

        # dodges and wavedashes can mess up correctly arriving, so we use them only if we really need them
        if (
                (
                        self.allow_dodges_and_wavedashes
                        and norm(car.velocity) < target_speed - 600
                        and car.boost < 20
                        and not self.backwards
                )
                or not self.travel.driving  # a dodge/wavedash is in progress
        ):
            self.action = self.travel
        else:
            self.action = self.drive

        self.action.step(dt)
        self.controls = self.action.controls

        self.finished = self.car.time >= self.arrival_time

    def render(self, draw: DrawingTool):
        self.drive.render(draw)

        if self.target_direction is not None:
            draw.color(draw.lime)
            draw.triangle(self.target - self.target_direction * 250, self.target_direction)
