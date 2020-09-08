from gosling.routines import *
from gosling.objects import GoslingAgent
from gosling.utils import defaultPD, defaultThrottle
from physics.math import Vec3
from physics.simulations import Ball
from math import acos, sin, degrees
from rlbot.utils.structures.ball_prediction_struct import Slice
from typing import Optional


class GameConstants:
    """"Ingame constants used for driving"""
    MAX_SPEED_NO_BOOST = 1410
    MAX_SPEED = 2300
    BOOST_BONUS_ACCELERATION = 991.66
    BOOST_CONSUMPTION_RATE = 33.33
    IN_GAME_FPS = 60
    FIELD_LENGTH = 5150
    CAP_X_IN_GOAL_LENGTH = 750
    ACCELERATION_FORMULA_B = 1600
    ACCELERATION_FORMULA_A = -1.02


class Intercept:
    """Intercepts the ball from the current location. """

    # Interception settings
    DETECT_MISS_RANGE = 150  # The range in which we validate if the car has passed the ball - and missed
    MAX_Z_INTERCEPT = 100  # The maximum height at which the car will try to flip to hit the ball
    MAX_Z_FLIP = 80
    MAX_TIME_REMAING_BEFORE_FLIP = 0.5

    # Flip settings
    FLIP_RANGE = 1000  # The range at which to flip

    # Ball prediction settings
    SLICE_ANGLE = 90  # Angle of the cone in front of the car for which interceptions are considered
    TUNABLE_DELAY = 0.2  # Delay to reduce inaccuracies in ball predictions to prevent flipping prematurely
    INTERCEPTION_MARGIN = 50  # Max distance at which the simulation will classify as hitting the ball
    SIM_TIME_STEP = 1 / 30  # Time step for velocity simulations
    GRID_SEARCH_INTERVAL = 20  # How many steps per second to consider for interception analysis

    def run(self, agent: GoslingAgent):
        """Sets controls for the provided agent.

        :param agent: Gosling agent
        :type agent: GoslingAgent
        """
        target = self._get_target(agent)
        if self._detect_missed_ball(agent):
            agent.pop()
            return

        if target:
            self._control_with_intercept_point(agent, target)
        else:
            self._control_without_intercept_point(agent)

    @staticmethod
    def _calc_local_diff(agent: GoslingAgent, ball_pos: Vector3) -> Vector3:
        """Calculate the local vector from the agent to the ball.

        :param agent: Gosling agent object
        :type agent: GoslingAgent
        :param ball_pos: The position of the ball
        :type ball_pos: Vector3
        :returns: A vector describing the local vector from car to ball
        :rtype: Vector3
        """

        # Transforms the ball and car coordinates local coordinates of the car
        car_pos = agent.me.location.flatten()  # 2D coordinate of the car
        cos_theta = (car_pos.dot(ball_pos)) / (car_pos.magnitude() * ball_pos.magnitude())
        sin_theta = sin(acos(cos_theta))

        # Local coordinates from the car its perspective
        car_to_ball = ball_pos - car_pos  # Relative coord wrt the car
        local_diff = Vector3(car_to_ball.x * cos_theta - car_to_ball.y * sin_theta,
                             car_to_ball.x * sin_theta + car_to_ball.y * cos_theta, 0).flatten()

        return local_diff

    @staticmethod
    def _time_to_idx(time: float) -> int:
        """Converts time to an index for the BallPrediction struct.

        :param time: Time for which to retrieve the index
        :type time: float
        :returns: Index integer
        :rtype: int
        """
        return round(time * GameConstants.IN_GAME_FPS)

    @staticmethod
    def _get_max_acceleration(vel: float, boost: bool = True) -> float:
        """"Get the maximum acceleration for a given velocity."""
        if vel > GameConstants.MAX_SPEED_NO_BOOST:
            return boost * GameConstants.BOOST_BONUS_ACCELERATION
        else:
            return vel * GameConstants.ACCELERATION_FORMULA_A + boost + GameConstants.ACCELERATION_FORMULA_B + \
                   GameConstants.BOOST_BONUS_ACCELERATION  # Coefficients for the velocity vs amax curve.

    def _in_range(self, time_left: float, dist_left: float, vel: float) -> bool:
        """Check whether to start maximum acceleration, Calculates if we reach the target distance,
        if we use maximum acceleration, accounts for the amount of boost we have left
        """
        total_steps = round(time_left / self.SIM_TIME_STEP)  # Amount of steps to loop through

        # Physics simulation stepping starts here
        for i in range(total_steps):
            a = Intercept._get_max_acceleration(vel, True)
            vel = vel + a * self.SIM_TIME_STEP
            dist_left -= vel * self.SIM_TIME_STEP

            # Start if we can reach the target within the given time by max acceleration
            if -self.INTERCEPTION_MARGIN < dist_left < self.INTERCEPTION_MARGIN:
                return True
        # we do not reach the target with full boost
        return False

    def _get_target(self, agent: GoslingAgent) -> Optional[Slice]:
        """"Retrieves the interception target"""
        # For predicting the location of the ball for the coming 6 seconds.
        ball_prediction = Ball.get_ball_prediction()
        min_t, max_t = 0, ball_prediction.num_slices / 60  # By default (0, 6) - From RLBOT

        for i in range(min_t, round(max_t * self.GRID_SEARCH_INTERVAL)):  # Grid
            time = i / self.GRID_SEARCH_INTERVAL
            target = ball_prediction.slices[self._time_to_idx(time)]

            # Skip if the target is too high or low!
            if target.physics.location.z > self.MAX_Z_INTERCEPT:
                continue

            offset_angle = Vec3.from_other_vec(
                self._calc_local_diff(agent, Vector3(target.physics.location))).angle_2d(Vec3(x=0, y=1, z=0))
            if degrees(offset_angle) < self.SLICE_ANGLE:
                ball_distance = (agent.me.location - Vector3(target.physics.location)).magnitude()

                if self._in_range(time, ball_distance, agent.me.velocity.magnitude()):
                    return target
        return None

    def _control_with_intercept_point(self, agent: GoslingAgent, target: Slice):
        """""Controls the agent towards the given interception point"""
        t_rem = target.game_seconds - agent.time  # Time remaining for impact

        self._goto_target(agent, Vector3(target.physics.location.x,
                                         target.physics.location.y,
                                         target.physics.location.z))
        dist_left = (agent.me.location - agent.ball.location).magnitude()

        if dist_left < self.FLIP_RANGE:
            dz = agent.ball.location.z - agent.me.location.z
            if dz < self.MAX_Z_FLIP and t_rem < self.MAX_TIME_REMAING_BEFORE_FLIP:
                # print(f"Remaining time: {t_rem} Target Z: {target.physics.location.z}"
                #       f" Agent Z: {agent.me.location.z} Ball Z: {agent.ball.location.z}")

                flip_target = agent.me.local(agent.ball.location - agent.me.location)
                agent.pop()
                agent.push(flip(flip_target))  # flip to local target
                return

    def _control_without_intercept_point(self, agent: GoslingAgent):
        """Controls the agent in case no interception point is found. Can switch to Aerial."""
        self._goto_target(agent, agent.ball.location)

    def _detect_missed_ball(self, agent: GoslingAgent) -> bool:
        """"Checks if the car is close to the ball and missed a shot. """
        xy_diff = (agent.ball.location - agent.me.location).flatten()
        if self.DETECT_MISS_RANGE > xy_diff.magnitude():
            xy_norm = xy_diff.normalize()
            vel_norm = (agent.me.velocity - agent.ball.velocity).flatten().normalize()

            # Negative dot implies negative projection -> Ball is behind the agent!
            if vel_norm.dot(xy_norm) < 0:
                # print(f"Missed ball! {vel_norm.dot(xy_norm)}")
                return True
        return False

    def _goto_target(self, agent: GoslingAgent, target: Vector3):
        """"Drives the agent to a particular target. """
        # Some adjustment to the final target to ensure it's inside the field and we dont try to drive through
        # any goalposts to reach it
        if abs(agent.me.location[1]) > GameConstants.FIELD_LENGTH:
            target[0] = cap(target[0], -GameConstants.CAP_X_IN_GOAL_LENGTH, GameConstants.CAP_X_IN_GOAL_LENGTH)

        local_target = agent.me.local(target - agent.me.location)
        angles = defaultPD(agent, local_target)
        defaultThrottle(agent, GameConstants.MAX_SPEED)

        agent.controller.boost = False
        agent.controller.handbrake = True if abs(angles[1]) > 2.3 else agent.controller.handbrake
