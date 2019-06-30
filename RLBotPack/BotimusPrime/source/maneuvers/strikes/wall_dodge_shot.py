from maneuvers.kit import *

from maneuvers.strikes.dodge_strike import DodgeStrike

class WallDodgeShot(DodgeStrike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.pos[2] > 1000 and abs(ball.pos[0]) > Arena.size[0] - 300 \
        and (ground_distance(car, ball) + ball.pos[2] - car.pos[2]) / estimate_max_car_speed(car) * 1.2 < ball.t - car.time

    def configure(self, intercept: Intercept):
        self.arrive.drive.drive_on_walls = True
        ball = intercept.ball

        self.arrive.target = vec3(Arena.size[0] * sign(ball.pos[0]), ball.pos[1], ball.pos[2])

        target_direction = direction(ball, self.target)
        target_direction[0] = 0

        dist_to_wall = Arena.size[0] - abs(ball.pos[0])

        self.arrive.target_direction = normalize(target_direction)
        self.arrive.time = intercept.time
        
        self.dodge.jump.duration = 0.05 + clamp((dist_to_wall - 92) / 500, 0, 1)
        if not intercept.is_viable:
            self.finished = True