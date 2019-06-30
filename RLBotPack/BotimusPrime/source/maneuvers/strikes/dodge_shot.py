from maneuvers.kit import *

from maneuvers.strikes.dodge_strike import DodgeStrike

class DodgeShot(DodgeStrike):

    max_base_height = 220

    def intercept_predicate(self, car: Car, ball: Ball):
        max_height = align(car, ball, self.target) * 60 + self.max_base_height
        contact_ray = ball.wall_nearby(max_height)
        return (
            norm(contact_ray.start) > 0
            and ball.pos[2] < max_height + 50
            and (Arena.inside(ball.pos, 100) or distance(ball, self.target) < 1000)
            and abs(car.pos[0]) < Arena.size[0] - 300
        )

    def configure(self, intercept: Intercept):
        super().configure(intercept)

        ball = intercept.ball
        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.vel, target_direction * 4000)
        
        self.arrive.target = intercept.ground_pos - hit_dir * 100
        self.arrive.target_direction = hit_dir
