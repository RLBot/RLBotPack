from maneuvers.kit import *

from maneuvers.strikes.strike import Strike

class WallShot(Strike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.pos[2] > 800 and abs(ball.pos[0]) > Arena.size[0] - 150 \
        and (ground_distance(car, ball) + ball.pos[2] - car.pos[2]) / estimate_max_car_speed(car) * 1.2 < ball.t - car.time

    def configure(self, intercept: Intercept):
        self.arrive.drive.drive_on_walls = True
        ball = intercept.ball

        #dist_to_side_wall = Arena.size[0] - abs(ball.pos[0])
        #dist_to_back_wall = Arena.size[1] - abs(ball.pos[1])
        #
        #check which wall is closer
        # if dist_to_side_wall < dist_to_back_wall:
        #     self.arrive.target = vec3(Arena.size[0] * sign(ball.pos[0]), ball.pos[1], ball.pos[2])
        #     wall_index = 0
        # else:
        #     self.arrive.target = vec3(ball.pos[0], Arena.size[1] * sign(ball.pos[1]), ball.pos[2])
        #     wall_index = 1

        self.arrive.target = vec3(Arena.size[0] * sign(ball.pos[0]), ball.pos[1], ball.pos[2])

        target_direction = direction(ball, self.target)
        target_direction[0] = 0

        self.arrive.target_direction = normalize(target_direction)
        self.arrive.time = intercept.time