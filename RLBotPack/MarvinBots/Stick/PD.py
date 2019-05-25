from util import *


THROTTLE_ACCEL = 1600
BREAK_ACCEL = 3500

THROTTLE_MAX_SPEED = 1400
MAX_CAR_SPEED = 2300

DT = 1 / 60


def tfs(throttlespeed):
    """time until throttle full stop"""
    return abs(throttlespeed) / BREAK_ACCEL + DT


# def tdv(rel_vel):
#     """time until throttle desired velocity"""
#     rate = 2100 if rel_vel > 0 else 3600
#     return abs(rel_vel) / rate + 1 / 99


def pfs(pitchspeed):
    """time until pitch full stop"""
    return abs(pitchspeed) / 66 + DT


def yfs(yawspeed):
    """time until yaw full stop"""
    return abs(yawspeed) / 50 + DT


def rfs(rollspeed):
    """time until roll full stop"""
    return abs(rollspeed) / 99 + DT


def curve1(x):
    if x > .5:
        x = 1 - Range(x, 1)
    s = x * x * x * 5e5
    return Range(s, 1)


def steer_point(ang, angvel):
    """PD steer to point"""
    return curve1(Range180(ang - angvel * DT, PI))


def throttle_point(loc, vel, brakes=1):
    """PD throttle to point"""
    return sign(loc - brakes * tfs(vel) * vel) * Range((abs(loc) + abs(vel)) * DT, 1)


def throttle_velocity(vel, dspeed, lthrottle):
    """PD throttle to velocity"""
    vel = vel + throttle_acc(lthrottle, vel) * DT
    dacc = (dspeed - vel) / DT * Sign(dspeed)
    if dacc > 0:
        return Range(dacc / (throttle_acc(1, vel) + 1e-9), 1) * Sign(dspeed)
    elif -3600 < dacc <= 0:
        return 0
    else:
        return -1


def throttle_acc(throttle, vel):
    if throttle * vel < 0:
        return -3600 * sign(vel)
    elif throttle == 0:
        return -525 * sign(vel)
    else:
        return (-THROTTLE_ACCEL / THROTTLE_MAX_SPEED * min(abs(vel), THROTTLE_MAX_SPEED) + THROTTLE_ACCEL) * throttle


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
    if vel < THROTTLE_MAX_SPEED:
        if dvel < 0:
            threshold = 800
        else:
            threshold = 250
    else:
        threshold = 50
    return rel_vel > threshold
