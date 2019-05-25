import math

import numpy as np
from RLUtilities.LinearAlgebra import dot, angle_between, vec2
from RLUtilities.Simulation import Input

from util import distance_2d, velocity_2d, z0, line_backline_intersect


class Dribbling:
    __slots__ = ['ball', 'car', 'goal', 'p_s', 'controls', 'finished']

    def __init__(self, car, ball, goal):

        self.car = car
        self.ball = ball
        self.goal = goal
        self.controls = Input()
        self.p_s = 0

        self.finished = False

    def step(self, dt):
        # direction of ball relative to center of car (where should we aim)
        # direction of ball relative to yaw of car (where should we aim verse where we are aiming)
        local_bot_to_ball = dot(self.ball.pos - self.car.pos, self.car.theta)
        angle_front_to_ball = math.atan2(local_bot_to_ball[1], local_bot_to_ball[0])
        # distance between bot and ball
        distance = distance_2d(self.car.pos, self.ball.pos)
        # direction of ball velocity relative to yaw of car (which way the ball is moving verse which way we are moving)
        if velocity_2d(self.ball.vel) < 1e-10:
            angle_car_forward_to_ball_vel = 0
        else:
            angle_car_forward_to_ball_vel = angle_between(z0(self.car.forward()), z0(self.ball.vel))
        # magnitude of ball_bot_angle (squared)
        ball_bot_diff = (self.ball.vel[0] ** 2 + self.ball.vel[1] ** 2) - (self.car.vel[0] ** 2 + self.car.vel[1] ** 2)
        # p is the distance between ball and car
        # i is the magnitude of the ball's velocity (squared) the i term would normally
        # be the integral of p over time, but the ball's velocity is essentially that number
        # d is the relative speed between ball and car
        # note that bouncing a ball is distinctly different than balancing something that doesnt bounce
        # p_s is the x component of the distance to the ball
        # d_s is the one frame change of p_s, that's why p_s has to be global

        # we modify distance and ball_bot_diff so that only the component along the car's path is counted
        # if the ball is too far to the left, we don't want the bot to think it has to drive forward
        # to catch it
        distance_y = math.fabs(distance * math.cos(angle_front_to_ball))
        distance_x = math.fabs(distance * math.sin(angle_front_to_ball))
        # ball moving forward WRT car yaw?
        forward = False
        if math.fabs(angle_car_forward_to_ball_vel) < math.radians(90):
            forward = True
        # first we give the distance values signs
        if forward:
            d = ball_bot_diff
            i = (self.ball.vel[0] ** 2 + self.ball.vel[1] ** 2)
        else:
            d = -ball_bot_diff
            i = -(self.ball.vel[0] ** 2 + self.ball.vel[1] ** 2)

        if math.fabs(math.degrees(angle_front_to_ball)) < 90:
            p = distance_y

        else:
            p = -1 * distance_y
        # this is the PID correction.  all of the callibration goes on right here
        # there is literature about how to set the variables but it doesn't work quite the same
        # because the car is only touching the ball (and interacting with the system) on bounces
        # we run the PID formula through tanh to give a value between -1 and 1 for steering input
        # if the ball is lower we have no velocity bias
        bias_v = 600000  # 600000

        # just the basic PID if the ball is too low
        if self.ball.pos[2] < 120:
            correction = np.tanh((20 * p + .0015 * i + .006 * d) / 500)
        # if the ball is on top of the car we use our bias (the bias is in velocity units squared)
        else:
            correction = np.tanh((20 * p + .0015 * (i - bias_v) + .006 * d) / 500)
        # makes sure we don't get value over .99 so we dont exceed maximum thrust
        self.controls.throttle = correction * .99
        # anything over .9 is boost
        if correction > .99:
            self.controls.boost = True
        else:
            self.controls.boost = False

        # this is the PID steering section
        # p_s is the x component of the distance to the ball (relative to the cars direction)
        # d_s is the on frame change in p_s

        # we use absolute value and then set the sign later
        d_s = math.fabs(self.p_s) - math.fabs(distance_x)
        self.p_s = math.fabs(distance_x)
        # give the values the correct sign
        if angle_front_to_ball < 0:
            self.p_s = -self.p_s
            d_s = -d_s
        # d_s is actually -d_s ...whoops
        d_s = -d_s
        max_bias = 35
        backline_intersect = line_backline_intersect(self.goal.center[1], vec2(self.car.pos),
                                                     vec2(self.car.forward()))
        if abs(backline_intersect) < 1000 or self.ball.pos[2] > 200:
            bias = 0
        # Right of the ball
        elif -850 > backline_intersect:
            bias = max_bias
        # Left of the ball
        elif 850 < backline_intersect:
            bias = -max_bias

        # the correction settings can be altered to change performance
        correction = np.tanh((100 * (self.p_s + bias) + 1500 * d_s) / 8000)
        # apply the correction
        self.controls.steer = correction
