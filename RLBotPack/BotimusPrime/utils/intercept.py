from rlutilities.simulation import Car, Ball
from rlutilities.mechanics import Aerial
from rlutilities.linear_algebra import look_at

from utils.vector_math import *
from utils.math import *
from utils.misc import *


class Intercept:
    def __init__(self, car: Car, ball_predictions, predicate: callable = None, backwards=False):
        self.ball: Ball = None
        self.is_viable = True

        #find the first reachable ball slice that also meets the predicate
        speed = 1000 if backwards else estimate_max_car_speed(car)
        # for ball in ball_predictions:
        for ball in ball_predictions:
            if estimate_time(car, ball.position, speed, -1 if backwards else 1) < ball.time - car.time \
            and (predicate is None or predicate(car, ball)):
                self.ball = ball
                break

        #if no slice is found, use the last one
        if self.ball is None:
            if not ball_predictions:
                self.ball = Ball()
            else:
                self.ball = ball_predictions[-1]
            self.is_viable = False

        self.time = self.ball.time
        self.ground_pos = ground(self.ball.position)
        self.position = self.ball.position

class AerialIntercept:
    def __init__(self, car: Car, ball_predictions, predicate: callable = None):
        self.ball: Ball = None
        self.is_viable = True

        #find the first reachable ball slice that also meets the predicate
        test_car = Car(car)
        test_aerial = Aerial(car)
        
        for ball in ball_predictions:
            test_aerial.target = ball.position
            test_aerial.arrival_time = ball.time

            # fake our car state :D
            dir_to_target = ground_direction(test_car.position, test_aerial.target)
            test_car.velocity = dir_to_target * max(norm(test_car.velocity), 1200)
            test_car.orientation = look_at(dir_to_target, vec3(0,0,1))

            if test_aerial.is_viable() and (predicate is None or predicate(car, ball)):
                self.ball = ball
                break

        #if no slice is found, use the last one
        if self.ball is None:
            self.ball = ball_predictions[-1]
            self.is_viable = False

        self.time = self.ball.time
        self.ground_pos = ground(self.ball.position)
        self.position = self.ball.position
