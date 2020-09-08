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

    car_rotation = Rotator(0, 1.57, 0)
    car_loc_x_range = [-2000, 2000]
    car_loc_y_range = [-2100, -300]
    car_loc_z = 17.02

    # Fraction between car and goal location to place the ball on
    goal_car_vec_to_ball_start_location_scale_range = [0.75, 0.95]


class DribbleEasy(BaseScenario):
    """ For testing dribbling. Spawns the car in front of the ball perfectly in line with the orange goal.

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
        """Reinitialise this scenario when called. Is called upon initialization and when the reset conditions are met.ç

        :return: The freshly initialized game state for this scenario
        :rtype: GameState, optional
        """
        self.timer = 0.0

        car_pos = Vec3(random.uniform(*Constants.car_loc_x_range),
                       random.uniform(*Constants.car_loc_y_range),
                       Constants.car_loc_z)

        # Creates a vec between the goal location and the car location, to init the ball
        random_range = Constants.goal_car_vec_to_ball_start_location_scale_range
        length_fraction = (random_range[0] + (random_range[1] - random_range[0]) * random.random())
        ball_pos = (car_pos - Constants.goal_location) * length_fraction + Constants.goal_location

        car_state = CarState(physics=Physics(
            location=car_pos,
            velocity=Vector3(0, -100, 0),
            rotation=Constants.car_rotation,
            angular_velocity=Vector3(0, 0, 0)),
            boost_amount=100)

        ball_state = BallState(physics=Physics(
            location=ball_pos + Vec3(0, 0, 40),
            velocity=Vector3(0, 0, 5),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vector3(0, 0, 0)
        ))

        return GameState(
            cars={0: car_state},
            ball=ball_state
        )
