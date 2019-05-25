from util import *


def tfs(throttlespeed):
    """time until throttle full stop"""
    return abs(throttlespeed) / 3600 + 1 / 60


def tdv(rel_vel):
    """time until throttle desired velocity"""
    rate = 2100 if rel_vel > 0 else 9000
    return abs(rel_vel) / rate + 1 / 99


def pfs(pitchspeed):
    """time until pitch full stop"""
    return abs(pitchspeed) / 66 + 1 / 60


def yfs(yawspeed):
    """time until yaw full stop"""
    return abs(yawspeed) / 50 + 1 / 50


def rfs(rollspeed):
    """time until roll full stop"""
    return abs(rollspeed) / 99 + 1 / 60


def curve1(x):
    if x > .5:
        x = 1 - Range(x, 1)
    s = x * x * x * 5e5
    return Range(s, 1)


def steer_point(ang, angvel):
    """PD steer to point"""
    return curve1(Range180(ang - angvel / 55, PI))


def throttle_point(loc, vel, brakes=1):
    """PD throttle to point"""
    return sign(loc - brakes * tfs(vel) * vel) * Range((abs(loc) + abs(vel)) / 60, 1)


def throttle_velocity(vel, dspeed, lthrottle):
    """PD throttle to velocity"""
    rel_vel = dspeed - vel - lthrottle * 9
    return Range(tdv(rel_vel) * 60 * sign(rel_vel), 1)


def yaw_point(ang, angvel):
    """PD yaw to point"""
    return sign(Range180(ang - angvel * yfs(angvel), 1)) * Range(abs(ang) * 5 + abs(angvel), 1)


def pitch_point(ang, angvel):
    """PD pitch to point"""
    return sign(Range180(-ang - angvel * pfs(angvel), 1)) * Range(abs(ang) * 5 + abs(angvel), 1)


def roll_point(ang, angvel):
    """PD roll to point"""
    return sign(Range180(-ang + angvel * rfs(angvel), 1)) * Range(abs(ang) * 4 + abs(angvel), 1)


def boost_velocity(vel, dvel, lboost=0):
    """P velocity boost control"""
    rel_vel = dvel - vel - lboost * 5
    if vel < 1400:
        if dvel < 0:
            threshold = 800
        else:
            threshold = 250
    else:
        threshold = 30
    return rel_vel > threshold
