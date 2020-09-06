from numpy import random
from physics.math import Vec3
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket
from scenario.base_scenario import BaseScenario
from typing import Optional


class Constants:
    timeout = 8.0
    y_limit_before_reset = 5000

    line_y_range = [-1200, 1200]
    line_x_side_offset = 2000
    line_x_side_range = [-300, 300]

    ball_loc_y_offset = 1000

    car_rotation = Rotator(0, 1.57, 0)

    car_height = 17.02
    ball_radius = 92.75


class SideShot(BaseScenario):
    """ General testing. Spawns the ball somewhat to the side, and the car 1000 units away in y direction. Requires
     slight redirection to get a proper shot at the orange goal. Always off center.

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

        left_or_right = (random.random() > 0.5) * 2 - 1
        x_location = random.uniform(*Constants.line_x_side_range) + left_or_right * Constants.line_x_side_offset

        car_pos = Vec3(x_location, random.uniform(*Constants.line_y_range), Constants.car_height)
        ball_pos = Vec3(car_pos.x, car_pos.y + Constants.ball_loc_y_offset, Constants.ball_radius)

        car_state = CarState(physics=Physics(
            location=car_pos,
            velocity=Vector3(0, -100, 0),
            rotation=Constants.car_rotation,
            angular_velocity=Vector3(0, 0, 0)),
            boost_amount=100)

        ball_state = BallState(physics=Physics(
            location=ball_pos,
            velocity=Vector3(0, 0, 1),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)
        ))

        return GameState(cars={0: car_state}, ball=ball_state)
