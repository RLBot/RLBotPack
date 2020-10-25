import math
import numpy as np

from rlbot.agents.base_agent import SimpleControllerState

from mechanic.base_mechanic import BaseMechanic
from mechanic.drive_turn_face_target import DriveTurnFaceTarget

from util.numerics import clip, sign
from util.physics.drive_1d_simulation_utils import (
    throttle_acceleration,
    BOOST_MIN_ACCELERATION,
    BOOST_MIN_TIME,
    BREAK_ACCELERATION,
    MAX_CAR_SPEED,
)
from util.render_utils import render_hitbox, render_car_text

PI = math.pi


class DriveArriveInTime(BaseMechanic):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn_mechanic = DriveTurnFaceTarget(self.agent, self.rendering_enabled)

    def get_controls(self, car, distance, target_loc, time) -> SimpleControllerState:

        turn_mechanic_controls = self.turn_mechanic.get_controls(car, target_loc)
        self.controls.steer = turn_mechanic_controls.steer
        self.controls.handbrake = turn_mechanic_controls.handbrake

        # useful variables
        delta_time = car.time - car.last_time
        if delta_time == 0:
            delta_time = 1 / 60

        car_forward_velocity = car.velocity.dot(car.rotation_matrix[:, 0])

        car_ang_vel_local_coords = np.dot(car.angular_velocity, car.rotation_matrix)

        # arrive in time
        desired_vel = clip(distance / max(time - delta_time, 1e-5), -2300, 2300)

        # throttle to desired velocity
        self.controls.throttle = throttle_velocity(car_forward_velocity, desired_vel, delta_time)

        # boost to desired velocity
        self.controls.boost = not self.controls.handbrake and boost_velocity(
            car_forward_velocity, desired_vel, delta_time
        )

        # This makes sure we're not powersliding
        # if the car is spinning the opposite way we're steering towards
        if car_ang_vel_local_coords[2] * self.controls.steer < 0:
            self.controls.handbrake = False
        # and also not boosting if we're sliding the opposite way we're throttling towards.
        if car_forward_velocity * self.controls.throttle < 0:
            self.controls.handbrake = self.controls.boost = False

        # rendering
        if self.rendering_enabled:
            text_list = [
                f"target_height : {target_loc[2]}",
                f"desired_vel : {desired_vel:.2f}",
                f"time : {time:.2f}",
                f"throttle : {self.controls.throttle:.2f}",
            ]

            color = self.agent.renderer.white()

            self.agent.renderer.begin_rendering()
            # rendering all debug text in 3d near the car
            render_car_text(self.agent.renderer, car, text_list, color)
            # rendering a line from the car to the target
            self.agent.renderer.draw_rect_3d(target_loc, 20, 20, True, self.agent.renderer.red())
            self.agent.renderer.draw_line_3d(car.location, target_loc, color)
            # hitbox rendering
            render_hitbox(
                self.agent.renderer, car.location, car.rotation_matrix, color, car.hitbox_corner, car.hitbox_offset,
            )
            self.agent.renderer.draw_rect_3d(car.location, 20, 20, True, self.agent.renderer.grey())
            self.agent.renderer.end_rendering()

        # updating status
        if distance < 20 and abs(time) < 0.05:
            self.finished = True
        if time < -0.05:
            self.failed = True

        return self.controls


def throttle_velocity(vel, desired_vel, dt):
    """Model based throttle to velocity"""
    desired_accel = (desired_vel - vel) / dt * sign(desired_vel)
    if desired_accel > 0:
        return clip(desired_accel / max(throttle_acceleration(vel, 1), 0.001)) * sign(desired_vel)
    elif -BREAK_ACCELERATION < desired_accel <= 0:
        return 0
    else:
        return -1


def boost_velocity(vel, desired_vel, dt):
    """Model based velocity boost control"""
    if desired_vel < vel or vel < 0 or vel > MAX_CAR_SPEED - 1:
        # don't boost if we want to go or we're going backwards or we're already at max speed
        return False
    else:
        desired_accel = (desired_vel - vel) / dt
        return desired_accel > (BOOST_MIN_ACCELERATION + throttle_acceleration(vel, 1) * BOOST_MIN_TIME / dt) / 2
