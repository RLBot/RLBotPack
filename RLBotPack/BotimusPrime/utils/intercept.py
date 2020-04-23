import math
from typing import Optional

from rlutilities.linear_algebra import norm, angle_between, dot
from rlutilities.simulation import Car, Ball
from utils.math import clamp

from utils.vector_math import distance, direction, ground


class Intercept:
    def __init__(self, car: Car, ball_predictions, predicate: callable = None, backwards=False):
        self.ball: Optional[Ball] = None
        self.car: Car = car
        self.is_viable = True

        # find the first reachable ball slice that also meets the predicate
        speed = 1000 if backwards else estimate_max_car_speed(car)

        for i in range(0, len(ball_predictions)):
            ball = ball_predictions[i]
            time = estimate_time(car, ball.position, speed, -1 if backwards else 1)
            if time < ball.time - car.time and (predicate is None or predicate(car, ball)):
                self.ball = ball
                break

        # if no slice is found, use the last one
        if self.ball is None:
            if not ball_predictions:
                self.ball = Ball()
                self.ball.time = math.inf
            else:
                self.ball = ball_predictions[-1]
            self.is_viable = False

        self.time = self.ball.time
        self.ground_pos = ground(self.ball.position)
        self.position = self.ball.position


def estimate_max_car_speed(car: Car):
    return clamp(max(norm(car.velocity), 1300) + car.boost * 100, 1600, 2300)


def estimate_time(car: Car, target, speed, dd=1) -> float:
    dist = distance(car, target)
    if dist < 100:
        return 0
    travel = dist / speed
    turning = angle_between(car.forward() * dd, direction(car, target)) / math.pi * 2
    if turning < 1:
        turning **= 2
    acceleration = (speed * dd - dot(car.velocity, car.forward())) / 2100 * 0.2 * dd / max(car.boost / 20, 1)
    return travel + acceleration + turning * 0.7
