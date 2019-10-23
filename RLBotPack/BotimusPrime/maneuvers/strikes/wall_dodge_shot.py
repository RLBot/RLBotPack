from maneuvers.kit import *

from maneuvers.strikes.dodge_strike import DodgeStrike

class WallDodgeShot(DodgeStrike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.position[2] > 1000 and abs(ball.position[0]) > Arena.size[0] - 300 \
        and (ground_distance(car, ball) + ball.position[2] - car.position[2]) / estimate_max_car_speed(car) * 1.2 < ball.time - car.time

    def configure(self, intercept: Intercept):
        self.arrive.drive.drive_on_walls = True
        ball = intercept.ball

        self.arrive.target = vec3(Arena.size[0] * sign(ball.position[0]), ball.position[1], ball.position[2])

        target_direction = direction(ball, self.target)
        target_direction[0] = 0

        dist_to_wall = Arena.size[0] - abs(ball.position[0])

        self.arrive.target_direction = normalize(target_direction)
        self.arrive.time = intercept.time
        
        self.dodge.jump.duration = 0.05 + clamp((dist_to_wall - 92) / 500, 0, 1)
        if not intercept.is_viable:
            self.finished = True