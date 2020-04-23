from maneuvers.strikes.dodge_strike import DodgeStrike
from rlutilities.simulation import Car, Ball
from utils.arena import Arena
from utils.intercept import Intercept
from utils.vector_math import ground_direction


class DodgeShot(DodgeStrike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.position[2] < 300

    def configure(self, intercept: Intercept):
        super().configure(intercept)

        ball = intercept.ball
        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.velocity, target_direction * 4000)
        
        self.arrive.target = intercept.ground_pos - hit_dir * 100
        self.arrive.target_direction = hit_dir
