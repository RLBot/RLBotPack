from numpy import random
from numpy.random import uniform, seed
from physics.math import Vec3
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket
from scenario.base_scenario import BaseScenario
from typing import Optional


class Constants:
    timeout = 4.0
    goal_location = Vec3(0, -5250, 600)

    ball_loc_x_range = [-1500, 1500]
    ball_loc_y_range = [-2000, 0]
    ball_loc_z_range = [100, 500]

    ball_vel_x_range = [-500, 500]
    ball_vel_y_range = [-1500, -2500]
    ball_vel_z_range = [-500, -500]

    car_rotation = Rotator(0, 1.57, 0)
    y_limit_before_reset = -5000


class Intercept(BaseScenario):
    """ For testing interception capabilities of the bot.

     :param packet: Update packet with information about the current game state
     :type packet: GameTickPacket"""

    def __init__(self, packet: GameTickPacket):
        super().__init__(packet)
        seed(0)

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
            location=Constants.goal_location.flatten(),
            velocity=Vec3(0, -100, 0),
            rotation=Constants.car_rotation,
            angular_velocity=Vector3(0, 0, 0)),
            boost_amount=100)

        # Normalize the direction we want the ball to go to, so we can manually define the speed
        ball_state = BallState(physics=Physics(
            location=Vec3(uniform(*Constants.ball_loc_x_range),
                          uniform(*Constants.ball_loc_y_range),
                          uniform(*Constants.ball_loc_z_range)),
            velocity=Vec3(uniform(*Constants.ball_vel_x_range),
                          uniform(*Constants.ball_vel_y_range),
                          uniform(*Constants.ball_vel_z_range)),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vec3(0, 0, 0)
        ))

        return GameState(cars={0: car_state}, ball=ball_state)
