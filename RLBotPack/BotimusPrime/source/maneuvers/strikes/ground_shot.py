from maneuvers.kit import *

from maneuvers.strikes.strike import Strike

class GroundShot(Strike):

    max_distance_from_wall = 110

    def intercept_predicate(self, car: Car, ball: Ball):
        if ball.pos[2] > 200 or abs(ball.pos[1]) > Arena.size[1] - 400:
            return False
        contact_ray = ball.wall_nearby(self.max_distance_from_wall)
        return norm(contact_ray.start) > 0 and abs(dot(ball.vel, contact_ray.direction)) < 250          

    def configure(self, intercept: Intercept):
        ball = intercept.ball

        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.vel, target_direction * 4000)
        
        self.arrive.target = intercept.ball.pos - hit_dir * 105
        self.arrive.target_direction = hit_dir
        self.arrive.time = intercept.time
