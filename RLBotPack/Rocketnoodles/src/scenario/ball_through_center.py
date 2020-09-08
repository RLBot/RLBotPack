from numpy import pi, cos, sin
from numpy.random import uniform, seed
from physics.math import Vec3
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import *
from scenario.base_scenario import BaseScenario
from typing import Optional


class Constants:
    timeout = 4.0  # Time after which the scenario resets
    radia_ball = 92.75  # Radius of the ball
    y_limit_before_reset = 5000

    # Angle at which the ball will be shot to the center of the field
    ball_min_angle = -0.5 * pi * 0.8  # 20 percent to the right of down
    ball_max_angle = (1.0 + 0.5 * 0.8) * pi  # 20 percent to the left of down

    # Ball initialization distance from center of the field
    ball_min_distance = 2000
    ball_max_distance = 4000

    # Ball speed
    ball_min_speed = 500
    ball_max_speed = 2000

    # Car initialization
    location_car = Vec3(0, -2000, 0)
    velocity_car = Vec3(0, -100, 0)
    rotation_car = Rotator(0, 1.57, 0)  # Half pi rad


class BallThroughCenter(BaseScenario):
    """ For testing interception capabilities of the bot. Passes the ball through the center of the field under
    different angles. The scenario ends when a timer is reached.

     :param packet: Update packet with information about the current game state
     :type packet: GameTickPacket
     """

    def __init__(self, packet: GameTickPacket):
        super().__init__(packet)
        seed(0)

    def reset_upon_condition(self, packet: GameTickPacket) -> Optional[GameState]:
        """This is called every step and can be used to modify the state of the game when a condition is met.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket
         :return: The state of the game if the scenario reset condition was met, otherwise none
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

        # Ball random angle from center, with velocity towards center
        angle_ball = uniform(Constants.ball_min_angle, Constants.ball_max_angle)
        distance = uniform(Constants.ball_min_distance, Constants.ball_max_distance)
        speed_ball = uniform(Constants.ball_min_speed, Constants.ball_max_speed)
        # print(f'distance: {distance}, Angle: {angle_ball}, Speed: {speed_ball}')

        # Determine x and y position and velocity from generated random angle
        x_ball, y_ball = distance * cos(angle_ball), distance * sin(angle_ball)
        x_vel_ball, y_vel_ball = speed_ball * -cos(angle_ball), speed_ball * -sin(angle_ball)

        ball_state = BallState(physics=Physics(
            location=Vec3(x_ball, y_ball, Constants.radia_ball),  # Always on the ground
            velocity=Vec3(x_vel_ball, y_vel_ball, 0),
            rotation=Rotator(0, 0, 0),
            angular_velocity=Vec3(0, 0, 0)
        ))

        car_state = CarState(physics=Physics(
            location=Constants.location_car,
            velocity=Constants.velocity_car,
            rotation=Constants.rotation_car,
            angular_velocity=Vector3(0, 0, 0)),
            boost_amount=100)

        return GameState(cars={0: car_state}, ball=ball_state)
