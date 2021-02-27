from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import dot, norm
from rlutilities.simulation import Field, sphere, Car, Ball
from tools.arena import Arena
from tools.intercept import Intercept
from tools.vector_math import ground_direction


class GroundStrike(Strike):
    """
    Strike the ball by just driving into it.
    Great for chipping the ball up when it's rolling towards you.
    """

    max_distance_from_wall = 120
    max_additional_time = 0.3

    def intercept_predicate(self, car: Car, ball: Ball):
        if ball.position[2] > 200 or abs(ball.position[1]) > Arena.size[1] - 100:
            return False
        contact_ray = Field.collide(sphere(ball.position, self.max_distance_from_wall))
        return norm(contact_ray.start) > 0 and abs(dot(ball.velocity, contact_ray.direction)) < 300

    def configure(self, intercept: Intercept):
        target_direction = ground_direction(intercept, self.target)
        strike_direction = ground_direction(intercept.ball.velocity, target_direction * 4000)
        
        self.arrive.target = intercept.position - strike_direction * 105
        self.arrive.target_direction = strike_direction
        self.arrive.arrival_time = intercept.time
