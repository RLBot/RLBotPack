from maneuvers.kit import *

from maneuvers.strikes.strike import Strike

class WallShot(Strike):

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.position[2] > 800 and abs(ball.position[0]) > Arena.size[0] - 150 \
        and (ground_distance(car, ball) + ball.position[2] - car.position[2]) / estimate_max_car_speed(car) * 1.2 < ball.time - car.time

    def configure(self, intercept: Intercept):
        self.arrive.drive.drive_on_walls = True
        ball = intercept.ball

        #dist_to_side_wall = Arena.size[0] - abs(ball.position[0])
        #dist_to_back_wall = Arena.size[1] - abs(ball.position[1])
        #
        #check which wall is closer
        # if dist_to_side_wall < dist_to_back_wall:
        #     self.arrive.target = vec3(Arena.size[0] * sign(ball.position[0]), ball.position[1], ball.position[2])
        #     wall_index = 0
        # else:
        #     self.arrive.target = vec3(ball.position[0], Arena.size[1] * sign(ball.position[1]), ball.position[2])
        #     wall_index = 1

        self.arrive.target = vec3(Arena.size[0] * sign(ball.position[0]), ball.position[1], ball.position[2])

        target_direction = direction(ball, self.target)
        target_direction[0] = 0

        self.arrive.target_direction = normalize(target_direction)
        self.arrive.time = intercept.time