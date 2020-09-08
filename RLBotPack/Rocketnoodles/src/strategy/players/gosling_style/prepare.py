from gosling.utils import defaultPD, defaultThrottle
from gosling.objects import *
import numpy as np
from typing import Optional


class GameConstants:
    max_speed_no_boost = 1400
    max_speed_boost = 2300
    x_field = 3500
    y_field = 4500
    ceiling_height = 2000


class Prepare:
    """ Position yourself behind the ball as seen from the enemy goal.

    :param center_player: Whether to prepare with an offset to the ball flipped over the y-axis.
    :type center_player: bool
    :param offset_in_ball_direction: How far to offset the target position from the ball.
    :type offset_in_ball_direction: float
    """
    QUICK_COMPENSATION_RANGE = 1500  # If far away quickly compensate by boosting. Otherwise do not.
    FINISH_DIST = 750
    CONTROL_VELOCITY_GAIN = 500

    def __init__(self, center_player=False, offset_in_ball_direction=2000):
        self.offset_in_ball_direction = offset_in_ball_direction
        self.center_player = center_player
        self.agent: Optional[GoslingAgent] = None

    def run(self, agent: GoslingAgent):
        """ Updates the controls for this Player.

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        prepare_to_shoot_target = self._get_prepared_location()
        self._go_to_target(prepare_to_shoot_target)

    def _get_prepared_location(self) -> Vector3:
        # Extend the vector from the foe goal through the ball
        direction = (self.agent.ball.location - self.agent.foe_goal.location).normalize()
        ball_direction_vector = self.offset_in_ball_direction * direction
        if self.center_player:
            ball_direction_vector.x *= -1

        ball_to_foe_goal = (self.agent.ball.location - self.agent.foe_goal.location)
        target = ball_direction_vector + ball_to_foe_goal + self.agent.foe_goal.location
        return self._clip_in_arena_bounds(target)

    def _go_to_target(self, target: Vector3):
        # Control our car
        defaultPD(self.agent, self.agent.me.local(target - self.agent.me.location))
        dist_to_target = (target - self.agent.me.location).magnitude()
        if dist_to_target < self.FINISH_DIST:
            self.agent.pop()

        # Quickly compensate if far away
        if dist_to_target > self.QUICK_COMPENSATION_RANGE:
            defaultThrottle(self.agent, GameConstants.max_speed_boost)
        else:
            defaultThrottle(self.agent, min(GameConstants.max_speed_no_boost, self._get_controlled_velocity(target)))

    def _get_controlled_velocity(self, target: Vector3) -> float:
        return (target - self.agent.me.location).magnitude() + self.CONTROL_VELOCITY_GAIN

    @staticmethod
    def _clip_in_arena_bounds(target: Vector3) -> Vector3:
        """Clips the location within the bounds of the arena"""
        return Vector3(float(np.clip(target.x, -GameConstants.x_field, GameConstants.x_field)),
                       float(np.clip(target.y, -GameConstants.y_field, GameConstants.y_field)),
                       float(np.clip(target.z, 0, GameConstants.ceiling_height)))
