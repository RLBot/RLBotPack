from maneuvers.strikes.dodge_strike import DodgeStrike
from rlutilities.simulation import Car, Ball
from tools.intercept import Intercept
from tools.math import abs_clamp


class CloseShot(DodgeStrike):
    """
    Shot at the goal, when the intercept is near the target goal.
    Instead of aiming at the center of the goal, aims for a position that is closer to the ball.
    """
    jump_time_multiplier = 1.1

    def intercept_predicate(self, car: Car, ball: Ball):
        # lower max height than DodgeStrike, because high jumps usually result in hitting the crossbar
        return ball.position[2] < 250

    def configure(self, intercept: Intercept):
        self.target[0] = abs_clamp(self.intercept.ground_pos[0], 400)
        super().configure(intercept)
