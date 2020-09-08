import numpy as np
import random
from physics.math import Vec3
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket
from scenario.base_scenario import BaseScenario
from typing import Optional


class Constants:
    timeout = 5.0
    y_limit_before_reset = -5000
    goal_location = Vec3(0, -5250, 600)

    ball_velocity = 2500
    shot_target_x_range = [-850, 850]
    shot_target_z_range = [1000, 2500]

    car_location = Vector3(0, goal_location.y, 17.02)
    car_rotation = Rotator(0, 1.57, 0)

    ball_loc_x_range = [-2500, 2500]
    ball_loc_y = 0
    ball_loc_z = 500


class ShootBallAtGoal(BaseScenario):
    """ Shoots ball from center to goal.

    :param packet: Information about the current game state needed for the timer
    :type packet: GameTickPacket
    """

    def __init__(self, packet: GameTickPacket):
        super().__init__(packet)

    def reset_upon_condition(self, packet: GameTickPacket) -> Optional[GameState]:
        """This is called every step and can be used to modify the state of the game when a condition is met.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket
         :return: The state of the game if the scenario reset condition was met, otherwise none.
         :rtype: GameState, optional
         """
        self._update_timer(packet)
        if packet.game_ball.physics.location.y < Constants.y_limit_before_reset or self.timer > Constants.timeout:
            return self.reset()
        else:
            return None

    def reset(self) -> GameState:
        """Reinitialise this scenario when called. Is called upon initialization and when the reset conditions are met.

        :return: The freshly initialized game state for this scenario
        :rtype: GameState, optional
        """
        self.timer = 0.0
        car_state = CarState(physics=Physics(
            location=Constants.car_location,
            velocity=Vector3(0, 100, 0),
            rotation=Constants.car_rotation,
            angular_velocity=Vector3(0, 0, 0)
        ), jumped=False, double_jumped=False, boost_amount=100)

        ball_pos = np.array([random.uniform(*Constants.ball_loc_x_range),
                             Constants.ball_loc_y,
                             Constants.ball_loc_z])

        goal_target = np.array([random.uniform(*Constants.shot_target_x_range),
                                Constants.goal_location.y,
                                random.uniform(*Constants.shot_target_z_range)])

        # Normalize the direction we want the ball to go to, so we can manually define the speed
        dir_vector = np.subtract(goal_target, ball_pos)
        direction = dir_vector / np.linalg.norm(dir_vector)
        ball_velocity = direction * Constants.ball_velocity

        ball_state = BallState(physics=Physics(
            location=np_vec3_to_vector3(ball_pos),
            velocity=np_vec3_to_vector3(ball_velocity),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)
        ))

        return GameState(cars={0: car_state}, ball=ball_state)


def np_vec3_to_vector3(direction):
    """ Converts numpy array to Vector3. """
    return Vector3(direction[0], direction[1], direction[2])


def vector3_to_np_vec3(direction):
    """ Converts Vector3 to numpy array. """
    return np.array([direction.x, direction.y, direction.z])
