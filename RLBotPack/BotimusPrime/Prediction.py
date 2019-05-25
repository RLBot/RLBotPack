import math
import time
from Unreal import Rotator, Vector3
from Objects import *
from Utils import * 

#only the first function was actually used in Botimus
#the rest is just me trying to rewrite chip's ball
#prediction in python and failing horribly

def predict(num_of_steps) -> Vector3:
    dt = 1 / 60
    g = Vector3(0, 0, -650)

    v = ball.velocity
    av = ball.av
    loc = ball.location

    steps = []

    for i in range(0, num_of_steps):

        r = 0.03
        a = g - v * r
        v += a * dt

        loc += v * dt + a * 0.5 * dt ** 2

        ground = False
        if v.size > 0:

            # floor
            if loc.z < ball.radius:
                loc.z = ball.radius
                if v.z > 210:  # bounce
                    v.z *= -0.6
                elif v.size > 565:  # sliding
                    v = v * (1 - .6 * dt)
                else:  # rolling
                    v = v * (1 - .2 * dt)

                ground = True

            # ceiling
            if loc.z > arena.z - ball.radius:
                v.z *= -1

            # side walls
            if abs(loc.x) > arena.x - ball.radius:
                v.x *= -1

            # goal walls
            if abs(loc.y) > arena.y - ball.radius:
                if (
                    abs(loc.x) < goal_dimensions.x - ball.radius
                    and loc.z < goal_dimensions.z - ball.radius
                ):
                    break
                v.y *= -1

            if loc.z < ball.radius:
                loc.z = ball.radius

        steps.append((loc, ground, i * dt + dt))

    return steps

