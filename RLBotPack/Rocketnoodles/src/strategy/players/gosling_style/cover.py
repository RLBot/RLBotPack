import numpy as np
from gosling.objects import *
from gosling.utils import defaultPD, defaultThrottle
from typing import Optional


class GameConstants:
    MAX_SPEED_NO_BOOST = 1400
    MAX_SPEED_BOOST = 2300
    X_FIELD = 4000
    Y_FIELD = 5000
    CEILING_HEIGHT = 2000


class Cover:
    """ Position yourself between the ball and your own goal.

    :param distance_ratio: At what ratio to position itself, 0 at own goal, 1 at ball
    :type distance_ratio: float
    """

    QUICK_COMPENSATION_RANGE = 3000  # Tunable parameter used to determine whether agent should boost.
    COVER_DONE_DIST = 500
    VELOCITY_CONTROL_GAIN = 100

    def __init__(self, distance_ratio: float = 0.4):
        self.distance_ratio = distance_ratio
        self.agent: Optional[GoslingAgent] = None

    def run(self, agent: GoslingAgent):
        """ Updates the controls for this Player.

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        cover_target = self._pos_between_ball_and_goal()
        self._check_done_covering(cover_target)
        self._control_agent(cover_target)

    def _get_dist_to_target(self, target: Vector3) -> float:
        return (target - self.agent.me.location).magnitude()

    def _pos_between_ball_and_goal(self) -> Vector3:
        goal_to_ball = self.agent.ball.location - self.agent.friend_goal.location
        target = self.distance_ratio * goal_to_ball + self.agent.friend_goal.location
        return self._clip_in_arena_bounds(target)

    def _control_agent(self, target: Vector3):
        self._control_agent_steer(target)
        self._control_agent_throttle(target)

    def _control_agent_steer(self, target: Vector3):
        defaultPD(self.agent, self.agent.me.local(target - self.agent.me.location))

    def _control_agent_throttle(self, target: Vector3):
        use_boost = self._get_dist_to_target(target) > self.QUICK_COMPENSATION_RANGE
        if use_boost:
            defaultThrottle(self.agent, GameConstants.MAX_SPEED_BOOST)
        else:
            defaultThrottle(self.agent, min(GameConstants.MAX_SPEED_NO_BOOST, self._get_control_velocity(target)))

    def _get_control_velocity(self, target: Vector3) -> float:
        return (target - self.agent.me.location).magnitude() + self.VELOCITY_CONTROL_GAIN

    def _check_done_covering(self, target: Vector3):
        if self._get_dist_to_target(target) < self.COVER_DONE_DIST:
            self.agent.pop()

    @staticmethod
    def _clip_in_arena_bounds(target: Vector3) -> Vector3:
        """Clips the location within the bounds of the arena"""
        return Vector3(float(np.clip(target.x, -GameConstants.X_FIELD, GameConstants.X_FIELD)),
                       float(np.clip(target.y, -GameConstants.Y_FIELD, GameConstants.Y_FIELD)),
                       float(np.clip(target.z, 0, GameConstants.CEILING_HEIGHT)))
