from maneuvers.kit import *

from maneuvers.strikes.strike import Strike
from rlutilities.simulation import Field, sphere

class GroundShot(Strike):

    max_distance_from_wall = 110
    max_additional_time = 0.3

    def intercept_predicate(self, car: Car, ball: Ball):
        if ball.position[2] > 200 or abs(ball.position[1]) > Arena.size[1] - 400:
            return False
        contact_ray = Field.collide(sphere(ball.position, self.max_distance_from_wall))
        return norm(contact_ray.start) > 0 and abs(dot(ball.velocity, contact_ray.direction)) < 150          
        # return dot(ball.velocity, vec3(0,0,1)) < 250

    def configure(self, intercept: Intercept):
        ball = intercept.ball

        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.velocity, target_direction * 4000)
        
        self.arrive.target = intercept.ball.position - hit_dir * 105
        self.arrive.target_direction = hit_dir
        self.arrive.time = intercept.time
