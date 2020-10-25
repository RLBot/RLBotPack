from skeleton.util.conversion import rotation_to_matrix
from util.collision_utils import (
    box_ball_collision_distance,
    box_ball_low_location_on_collision,
    box_ball_location_on_collision,
)
from util.physics.drive_1d_time import state_at_time_vectorized

import numpy as np


def get_ground_ball_intercept_state(game_data, box_location=None):
    ball_prediction = game_data.ball_prediction
    car = game_data.my_car
    box_location = car.location if box_location is None else box_location
    car_rot = rotation_to_matrix([0, car.rotation[1], car.rotation[2]])

    ball = game_data.ball

    hitbox_height = car.hitbox_corner[2] + car.hitbox_offset[2]
    origin_height = 17  # the car's elevation from the ground due to wheels and suspension

    # only accurate if we're already moving towards the target
    boost = np.array([car.boost] * len(ball_prediction), dtype=np.float64)

    location_slices = ball_prediction["physics"]["location"]

    distance_slices = box_ball_collision_distance(
        location_slices, box_location, car_rot, car.hitbox_corner, car.hitbox_offset, ball.radius,
    )
    time_slices = ball_prediction["game_seconds"] - game_data.time

    # not_too_high = location_slices[:, 2] < ball.radius + hitbox_height + origin_height
    not_too_high = location_slices[:, 2] < 300

    velocity = car.velocity[None, :]
    direction_slices = location_slices - box_location
    velocity = np.sum(velocity * direction_slices, 1) / np.linalg.norm(direction_slices, 2, 1)
    velocity = velocity.astype(np.float64)

    reachable = (state_at_time_vectorized(time_slices, velocity, boost)[0] > distance_slices) & not_too_high

    filtered_prediction = ball_prediction[reachable]

    target_loc = game_data.ball_prediction[-1]["physics"]["location"].astype(np.float64)
    target_vel = game_data.ball_prediction[-1]["physics"]["velocity"].astype(np.float64)
    target_dt = game_data.ball_prediction[-1]["game_seconds"] - game_data.time

    if len(filtered_prediction) > 0:
        target_loc = filtered_prediction[0]["physics"]["location"].astype(np.float64)
        target_vel = filtered_prediction[0]["physics"]["velocity"].astype(np.float64)
        target_dt = filtered_prediction[0]["game_seconds"] - game_data.time
        target_loc = box_ball_location_on_collision(
            target_loc, box_location, car_rot, car.hitbox_corner, car.hitbox_offset, ball.radius,
        )

    return target_loc, target_dt, target_vel
