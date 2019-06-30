from maneuvers.kit import *

from maneuvers.strikes.aerial_strike import AerialStrike

class AerialShot(AerialStrike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.pos[2] > 500

    def configure(self, intercept: AerialIntercept):
        ball = intercept.ball

        target_direction = ground_direction(ball, self.target)
        hit_dir = direction(ball.vel, target_direction * 4000)
        
        self.arrive.target = intercept.ground_pos - ground(hit_dir) * 130
        self.aerial.target = intercept.ball.pos - ground(hit_dir) * 130

        self.arrive.time = intercept.time
        self.aerial.t_arrival = intercept.time