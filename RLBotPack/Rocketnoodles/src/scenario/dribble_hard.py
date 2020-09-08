from numpy import random
from physics.math import Vec3
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket
from scenario.base_scenario import BaseScenario
from typing import Optional


class Constants:
    timeout = 8.0
    goal_location = Vec3(0, 5250, 600)
    y_limit_before_reset = 5000

    # Absolute positions for the ball
    ball_loc_x_range = [-1500, 1500]
    ball_loc_y_range = [-1500, 1500]
    ball_loc_z_range = [40, 160]

    ball_vel_xyz_range = [-300, 300]

    # Ranges relative to some offset from the ball pos for increased randomness
    car_loc_x_range = [-300, 300]
    car_loc_y_range = [-300, 300]
    car_loc_z_range = [40, 160]

    car_vel_xyz_range = [-300, 300]

    car_rotation = Rotator(0, 0, 1.57)
    car_offset_from_goal_ball_vec = 1500


class DribbleHard(BaseScenario):
    """ For testing dribbling. Spawns the car around the ball but with random distortions to make the challenge harder.

     :param packet: Update packet with information about the current game state
     :type packet: GameTickPacket"""

    def __init__(self, packet: GameTickPacket):
        super().__init__(packet)
        random.seed(0)

    def reset_upon_condition(self, packet: GameTickPacket) -> Optional[GameState]:
        """This is called every step and can be used to modify the state of the game when a condition is met.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket
         :return: The state of the game if the scenario reset condition was met, otherwise none.
         :rtype: GameState, optional
         """
        self._update_timer(packet)
        if packet.game_ball.physics.location.y > Constants.y_limit_before_reset or self.timer > Constants.timeout:
            return self.reset()
        else:
            return None

    def reset(self) -> GameState:
        """Reinitialise this scenario when called. Is called upon initialization and when the reset conditions are met.

        :return: The freshly initialized game state for this scenario
        :rtype: GameState, optional
        """
        self.timer = 0.0

        # Pick a ball location within defined bounds
        ball_pos = Vec3(random.uniform(*Constants.ball_loc_x_range),
                        random.uniform(*Constants.ball_loc_y_range),
                        random.uniform(*Constants.ball_loc_z_range))

        ball_state = BallState(physics=Physics(
            location=ball_pos,
            velocity=Vec3(random.uniform(*Constants.ball_vel_xyz_range),
                          random.uniform(*Constants.ball_vel_xyz_range),
                          random.uniform(*Constants.ball_vel_xyz_range)),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0),
        ))

        # Place the car relative to the ball, but with an offset and added randomness to make it harder
        car_pos = \
            ball_pos + \
            Vec3(random.uniform(*Constants.car_loc_x_range),
                 random.uniform(*Constants.car_loc_y_range),
                 random.uniform(*Constants.car_loc_z_range)) + \
            Constants.car_offset_from_goal_ball_vec * (ball_pos - Constants.goal_location).normalize()

        car_state = CarState(physics=Physics(
            location=car_pos,
            velocity=Vec3(random.uniform(*Constants.car_vel_xyz_range),
                          random.uniform(*Constants.car_vel_xyz_range),
                          random.uniform(*Constants.car_vel_xyz_range)),
            rotation=Constants.car_rotation,
            angular_velocity=Vector3(0, 0, 0)),
            boost_amount=100)

        return GameState(cars={0: car_state}, ball=ball_state)
