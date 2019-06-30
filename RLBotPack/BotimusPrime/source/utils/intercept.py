from RLUtilities.GameInfo import GameInfo
from RLUtilities.LinearAlgebra import *
from RLUtilities.Simulation import Car, Ball
from RLUtilities.Maneuvers import Aerial

from utils.vector_math import *
from utils.math import *
from utils.misc import *

class Intercept:
    def __init__(self, car: Car, ball_predictions, predicate: callable = None, backwards=False):
        self.ball: Ball = None
        self.is_viable = True

        #find the first reachable ball slice that also meets the predicate
        speed = 1100 if backwards else estimate_max_car_speed(car)
        for ball in ball_predictions:
            if estimate_time(car, ball.pos, speed, -1 if backwards else 1) < ball.t - car.time \
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

        self.time = self.ball.t
        self.ground_pos = ground(self.ball.pos)
        self.pos = self.ball.pos

class AerialIntercept:
    def __init__(self, car: Car, ball_predictions, predicate: callable = None, power = 1000):
        self.ball: Ball = None
        self.is_viable = True

        #find the first reachable ball slice that also meets the predicate
        test_aerial = Aerial(car, vec3(0, 0, 0), 0)
        for ball in ball_predictions:
            test_aerial.target = ball.pos
            test_aerial.t_arrival = ball.t
            test_aerial.calculate_course()
            if test_aerial.B_avg < power and (predicate is None or predicate(car, ball)):
                self.ball = ball
                break

        #if no slice is found, use the last one
        if self.ball is None:
            self.ball = ball_predictions[-1]
            self.is_viable = False

        self.time = self.ball.t
        self.ground_pos = ground(self.ball.pos)
        self.pos = self.ball.pos


class NearestIntercept:
    def __init__(self, pos: vec3, ball_predictions, predicate: callable = None):
        self.ball: Ball = None
        best_dist = 99999

        for ball in ball_predictions:
            dist = distance(pos, ball)
            if dist < best_dist and (predicate is None or predicate(pos, ball)):
                self.ball = ball
                best_dist = dist

        self.time = self.ball.t
        self.ground_pos = ground(self.ball.pos)
        self.pos = self.ball.pos
