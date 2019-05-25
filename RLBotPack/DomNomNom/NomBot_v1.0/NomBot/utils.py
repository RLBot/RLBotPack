
import math
import numpy as np
from functools import reduce

from .vector_math import *


UP = np.array([0.0, 0.0, 1.0])
UP.flags.writeable = False
STEER_R = +1
STEER_L = -1

# Indexes into pos/vel
TO_STATUE = 0  # There is a statue outside the playing fields. The direction the default observer cam faces.
TO_ORANGE = 1   # towards
TO_CEILING = 2  # UP is already taken

# Physics constants
BALL_RADIUS = 92.
MAX_CAR_SPEED = 2300.005
FLIP_SPEED_CHANGE = 500.0  # TODO: refine constant

# indexes into the output vector
OUT_VEC_THROTTLE = 0
OUT_VEC_STEER = 1
OUT_VEC_PITCH = 2
OUT_VEC_YAW = 3
OUT_VEC_ROLL = 4
OUT_VEC_JUMP = 5
OUT_VEC_BOOST = 6
OUT_VEC_HANDBRAKE = 7

def sanitize_output_vector(output_vector):
    return [
        clamp11(output_vector[0]),  # fThrottle
        clamp11(output_vector[1]),  # fSteer
        clamp11(output_vector[2]),  # fPitch
        clamp11(output_vector[3]),  # fYaw
        clamp11(output_vector[4]),  # fRoll
        clamp01(output_vector[5]),  # bJump
        clamp01(output_vector[6]),  # bBoost
        clamp01(output_vector[7]),  # bHandbrake
    ]

def estimate_turn_radius(car_speed):
    # https://docs.google.com/spreadsheets/d/1Hhg1TJqVUCcKIRmwvO2KHnRZG1z8K4Qn-UnAf5-Pt64/edit?usp=sharing
    # TODO: reverse speed?
    car_speed = clamp(car_speed, 0.0, MAX_CAR_SPEED)
    return (
        # -10
        +156
        +0.1         * car_speed
        +0.000069    * car_speed**2
        +0.000000164 * car_speed**3
        -5.62E-11    * car_speed**4
    )

class Car(object):
    def __init__(self, gamecar):
        self.pos = struct_vector3_to_numpy(gamecar.Location)
        self.vel = struct_vector3_to_numpy(gamecar.Velocity)
        self.angular_vel = struct_vector3_to_numpy(gamecar.AngularVelocity)
        self.boost = gamecar.Boost
        self.speed = mag(self.vel)
        self.to_global_matrix = rotation_to_mat(gamecar.Rotation)
        self.forward = self.to_global_matrix.dot(np.array([1.0, 0.0, 0.0]))
        self.right   = self.to_global_matrix.dot(np.array([0.0, 1.0, 0.0]))
        self.up      = self.to_global_matrix.dot(np.array(UP))
        self.on_ground = gamecar.bOnGround
        self.jumped = gamecar.bJumped
        self.double_jumped = gamecar.bDoubleJumped

class Ball(object):
    def __init__(self, ball=None):
        self.pos = Vec3(0,0,0)
        self.vel = Vec3(0,0,0)
        self.angular_vel = Vec3(0,0,0)
        if ball is None:
            return
        if isinstance(ball, Ball):
            self.pos = ball.pos
            self.vel = ball.vel
            return
        # c-struct
        self.pos = struct_vector3_to_numpy(ball.Location)
        self.vel = struct_vector3_to_numpy(ball.Velocity)
        self.angular_vel = struct_vector3_to_numpy(ball.AngularVelocity)

# A wrapper for the game_tick_packet
class EasyGameState(object):
    def __init__(self, game_tick_packet, team, car_index):
        gamecars = game_tick_packet.gamecars[:game_tick_packet.numCars]
        self.car = Car(game_tick_packet.gamecars[car_index])
        self.opponents = [ Car(c) for c in gamecars if c.Team != team]
        self.allies = [ Car(c) for i,c in enumerate(gamecars) if c.Team == team and i!=car_index]
        self.ball = Ball(game_tick_packet.gameball)
        self.time = game_tick_packet.gameInfo.TimeSeconds
        self.enemy_goal_dir = 1.0 if team==0 else -1.0  # Which side of the Y axis the goal is.
        self.enemy_goal_center = Vec3(0,  self.enemy_goal_dir*5350, 200)
        self.own_goal_center   = Vec3(0, -self.enemy_goal_dir*5350, 200)
        self.is_kickoff_time = not game_tick_packet.gameInfo.bBallHasBeenHit

class GraduatedAgent:
    name = "Agent"
    team = -1
    index = -1
    student = None
    
    def __init__(self, student_class, team, index):
        self.name = "Agent"
        self.team = team
        self.index = index
        self.student = student_class()
        
    def get_output_vector(self, game_tick_packet):
        s = EasyGameState(game_tick_packet, self.team, self.index)
        i = self.student.get_output_vector(s)
        return sanitize_output_vector(i)

def graduate_student_into_agent(student_class, team, index):
    return GraduatedAgent(student_class, team, index)

def main():
    import sys
    import os
    os.chdir(os.path.dirname(__file__))
    os.system('python doms_runner.py')
    sys.exit()

if __name__ == '__main__':
    main()
