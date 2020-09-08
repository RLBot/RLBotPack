from gosling.objects import *
from gosling.routines import *
from gosling.utils import defaultPD, defaultThrottle
from physics.math import Vec3
from typing import Optional


class Dribble:
    """ Dribble with the ball to a particular target.

    :param target: The target to which we will dribble
    :type target: Vec3
    :param flick: Whether to flick in the end or not to reach the target
    :type flick: bool
    """
    NEAR_BALL_CONTROL_RANGE = 500
    STEP = 1 / 60
    FLICK_DISTANCE = 2500

    BALL_ACQUISITION_RANGE = 350
    BALL_CONTROL_XY_OFFSET = 25
    BALL_CONTROL_MAX_THROTTLE = 500
    BALL_CONTROL_ACCELERATION = 500

    APPROACH_MAX_CONTROL_VELOCITY = 800
    APPROACH_BASE_VELOCITY = 300
    APPROACH_MINIMUM_VELOCITY = 2300
    APPROACH_VELOCITY_COMPENSATION = 25
    APPROACH_VELOCITY_TUNING = 2

    def __init__(self, target: Vec3, flick: bool = True):
        self.target = Vector3(target.x, target.y, target.z)
        self.flick = flick
        self.agent: Optional[GoslingAgent] = None

    def run(self, agent: GoslingAgent):
        """Dribble with the ball to a particular target

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        if self._distance_to_ball() < self.NEAR_BALL_CONTROL_RANGE:
            self._close_ball_control()
        else:
            self._approach_ball_control()
        self._flick_to_target(self.flick)

    def _distance_to_ball(self) -> float:
        return (self.agent.ball.location - self.agent.me.location).magnitude()

    def _close_ball_control(self):
        defaultPD(self.agent, self._get_close_local_target())
        defaultThrottle(self.agent, self._get_close_throttle())

    def _get_close_local_target(self) -> Vector3:
        offset = -(self.target - self.agent.ball.location).normalize() * self.BALL_CONTROL_XY_OFFSET
        return self.agent.me.local(self._get_future_ball_center() + offset - self.agent.me.location)

    def _get_close_throttle(self) -> float:
        future_agent_location = self.agent.me.location + self.agent.me.velocity * self.STEP
        dist_to_target = (self._get_future_ball_center() - future_agent_location).magnitude()
        acceleration_target = self.BALL_CONTROL_ACCELERATION * (dist_to_target / self.NEAR_BALL_CONTROL_RANGE) ** 1.25
        return max((self.agent.ball.velocity.magnitude() + acceleration_target), self.BALL_CONTROL_MAX_THROTTLE)

    def _get_future_ball_center(self) -> float:
        return self.agent.ball.location + self.agent.ball.velocity * self.STEP

    def _approach_ball_control(self):
        defaultPD(self.agent, self._get_approach_local_target())
        defaultThrottle(self.agent, self._get_approach_throttle())

    def _get_approach_throttle(self) -> float:
        own_speed = self.agent.me.velocity.magnitude()
        controlled_approach_velocity = self.APPROACH_BASE_VELOCITY + self.APPROACH_VELOCITY_TUNING * \
                                       self._distance_to_ball() - own_speed
        return min(controlled_approach_velocity, self.APPROACH_MINIMUM_VELOCITY)

    def _get_approach_local_target(self) -> Vector3:
        offset = (self.agent.ball.location - self.target).normalize() * self.BALL_ACQUISITION_RANGE
        vel_comp = - self.agent.me.velocity.normalize() * min(self._velocity_control(),
                                                              self.APPROACH_MAX_CONTROL_VELOCITY)
        target_car_pos = offset + self.agent.ball.location + vel_comp
        return self.agent.me.local(target_car_pos - self.agent.me.location)

    def _flick_to_target(self, flick: bool):
        if self._distance_to_target() < self.FLICK_DISTANCE and self._distance_to_ball() < \
                self.NEAR_BALL_CONTROL_RANGE and flick:
            vector_to_target = self.agent.me.local(self.target - self.agent.me.location)
            self.agent.pop()
            self.agent.push(flip(vector_to_target))

    def _distance_to_target(self) -> float:
        return (self.agent.me.location - self.target).magnitude()

    def _velocity_control(self) -> float:
        return self.agent.me.velocity.magnitude() * self.APPROACH_VELOCITY_COMPENSATION
