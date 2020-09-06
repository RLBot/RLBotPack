import math
from gosling.routines import aerial_shot, jump_shot, side
from gosling.objects import GoslingAgent, Vector3
from physics.math import Vec3
from physics.simulations.ball import *
from strategy.players.gosling_style.intercept import Intercept


class Keeper:
    """Calculates the future position of the ball and tries to intercept it."""

    JUMP_SHOT_HEIGHT_LIMIT = 300

    def __init__(self):

        self.agent: Optional[GoslingAgent] = None

    def run(self, agent: GoslingAgent):
        """
        Assigns which type of keeper routine we do.
        We use aerial_shot for shots higher than 300uu and we use jump_shot for shots lower than 300uu

        :param agent: Gosling agent.
        :type agent: GoslingAgent
        """
        self.agent = agent
        ball_slice_in_goal = Ball.predict_future_goal()
        if ball_slice_in_goal:
            self._choose_keeping_routine(ball_slice_in_goal)
        else:
            agent.pop()
            agent.push(Intercept())
            return

    def _choose_keeping_routine(self, ball_slice_in_goal: Slice):
        ball_intercept_location = self._future_intercept_location(ball_slice_in_goal)

        # The direction we shoot the ball towards
        shot_vector = Vector3(0, -side(self.agent.team), 0)

        # Determine which gosling routine we want to use for keeping
        if ball_intercept_location.physics.location.z > self.JUMP_SHOT_HEIGHT_LIMIT:
            self.agent.pop()
            self.agent.push(aerial_shot(Vector3(ball_intercept_location.physics.location),
                                        ball_intercept_location.game_seconds, shot_vector, None))
        else:
            self.agent.pop()
            self.agent.push(jump_shot(Vector3(ball_intercept_location.physics.location),
                                      ball_intercept_location.game_seconds, shot_vector, None))

    def _future_intercept_location(self, ball_slice_in_goal: Slice) -> Slice:
        time_of_goal = ball_slice_in_goal.game_seconds
        time_until_goal = time_of_goal - self.agent.time

        # Scaling linear based on ball velocity, 0 = 0.80, 3000 = 0.95
        vel_ball = Vec3.from_other_vec(Ball.predict_future_goal().physics.velocity).magnitude()
        factor = (vel_ball - 0) / (3000 - 0) * (0.95 - 0.8) + 0.8  # TODO: Imre - Explain please :p
        time_we_intercept = self.agent.time + time_until_goal * factor
        return Ball.find_slice_at_time(time_we_intercept)
