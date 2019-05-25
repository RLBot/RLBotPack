from PD import *


def controls(s):
    """Calculate controls"""

    s.dspeed = 2310
    s.brakes = (s.poG and (abs(s.sz) > 140 or abs(s.sx) > 130))
    s.throttle = throttle_point(s.sy, s.pyv, s.brakes)
    s.boost = to_boost(s) and boost_velocity(s.pyv, s.dspeed, s.lboost)
    s.steer = steer_point(s.sa, s.av)

    s.yaw = yaw_point(s.a, s.av)
    s.pitch = pitch_point(s.i, s.iv)
    s.roll = roll_point(s.r, s.rv) * (abs(s.a) < 0.2)

    s.powerslide = to_powerslide(s)

    # turn_around(s)

    jump_and_dodge(s)


def jump_and_dodge(s):

    if to_shoot(s):

        if to_jump(s):
            s.jumper = 1

        if to_dodge(s) and (s.vd < 999 or abs(s.pdT - s.odT) < .5):
            s.dodge = 1
            s.djL = "(s.tL + s.bL) / 2"

    if to_flip(s):
        s.dodge = 1
        s.djL = "s.tLs"

    s.jump = jump_handler(s) if s.jumper else 0

    if s.dodge and s.jcount > 0:
        s.jump = pre_dodge_handler(s)
        s.jumper = 0

    # jump for wavedash
    if (s.sd > 900 and 950 < (s.ty - s.yv / 2) and ang_dif(s.sa, s.pva, 1) < .02 and abs(s.sz) < 130 and
            s.pL[2] < 50 and s.poG and s.pB < 40 and 1050 < s.pvd < 2200 and s.gtime > .1):
        s.jump = 1

    wavedash(s)

    flip_handler(s)

    if s.poG and s.lljump != s.ljump:
        s.jump = s.ljump


def to_shoot(s):
    """Conditions to shoot"""
    if (s.offense and (abs(s.glinex) < 850 or Range180(s.gta - s.gpa, 1) < 0.1)) or s.kickoff:
        return 1
    if (not s.offense or abs(s.a) > .8) and abs(s.oglinex) > 1200:
        return 1
    return 0


def to_dodge(s):
    """Condidtions to dodge"""
    if abs(s.pL[2] - s.tL[2]) < 120 and s.jcount > 0 and s.gtime > 0.05:

        if s.fgd2 < 130 and s.dT < .35:
            return 1

        if s.ofd < 220 and abs(s.odT - s.pdT) < .5 and s.fgd2 < 180 and s.dT < .6:
            return 1

    return 0


def to_jump(s):
    """Conditions to jump"""

    s.zspeed = s.sz / (s.dT + 1e-4)
    s.jumpd = min(s.dT * 300, s.jcount * 220)
    s.boostd = 0.5 * 1058 * min(s.dT, s.pB / 33) ** 2

    if s.fd2 < 150 and 99 < s.fz < s.jumpd + max(s.boostd - s.jumpd, 0) and s.jcount > 0:
        if 200 < s.zspeed < 400 + max(s.boostd - 300, 0) / (s.dT + 1e-2):
            return 1

    if 150 < s.sz < s.jcount * 220 + 80:
        if s.sd2 < 130 and s.vd2 < 150:
            return 1

    s.d2pv = dist2d([s.tx - s.pxv * (s.dT + .04), s.ty - s.pyv * (s.dT + .04)])
    if (s.tz > 140 and ((s.tz < s.jcount * 250 + s.pB * 10 and s.d2pv < 100 and s.vd2 < 150))):
        return 1

    return 0


def to_flip(s):
    """Conditions to flip"""

    if (s.gtime > 0.05 or not s.poG) and not s.jumper and ang_dif(s.sa, s.pva, 1) < .06:

        if s.sd > min(s.pvd + 400, 2300) * (.8 + .4 * (abs(s.sa) < 0.5)) and s.pvd < abs(s.dspeed) - 250:

            if s.pB < 80 and s.pyv > 1640 or (s.pyv > 1120 and s.pB < 16) or (s.pyv > 960 and s.pB < 5) and abs(s.i) < .1:
                return 1

            # backflip
            if abs(s.sa) > 0.75 and s.pyv < -140:
                return 1

    return 0


def wavedash(s):
    """Conditions to wavedash"""
    if (s.jcount > 0 and s.pL[2] + s.pV[2] / 20 < 32 and abs(s.r) < 0.1 and abs(s.sa) < 0.04 and s.sy > 400 and
            0 < abs(s.pR[0] / U180) < 0.12 and not s.poG and s.pV[2] < -210):
        # Forward wavedash
        s.jump = not s.ljump
        s.pitch = -1
        s.yaw = s.roll = 0


def turn_around(s):
    """Turn around from facing backwards"""
    if s.poG and s.sd2 > 450 and abs(s.sa + s.av / 3) > 0.45:

        if abs(s.sa) > 0.98:
            s.steer = 1

        if s.sd2 > 600 and s.pyv < -90:
            if (abs(s.sa) < 0.98 and abs(s.av) > 0.5 and ang_dif(s.sa, s.pva, 1) < .25):
                s.powerslide = 1
            s.steer = -sign(s.steer)

    # three point turn
    if (s.poG and 20 < abs(s.sx) < 400 and abs(s.sy) < 200 and .35 < abs(s.sa) < .65 and
            abs(s.pyv) < 550 and dist3d(s.pV, s.tV) < 550):
        s.throttle = -sign(s.throttle)
        s.steer = -sign(s.steer)


def to_powerslide(s):
    """Condition to powerslide"""

    if (.2 < ang_dif(s.sa, s.av / 7, 1) < .8 and s.av * s.steer >= 0 and s.pyv * s.throttle >= 0 and
            abs(s.pxv) < 500 and .05 < abs(s.a) < .95):
        return 1

    if ang_dif(s.sa, s.pva, 1) < .15 and .15 < abs(s.sa) < .85 and not s.kickoff:
        return 1

    return 0


def to_boost(s):
    """Condition to boost"""
    return s.throttle == 1 and (abs(s.a) < .13 and abs(s.i) < .15 or s.poG)


def jump_handler(s):
    """Handling single and double jumps"""

    jump = 1 if s.poG or s.ljump and not s.poG and s.fz > 0 else 0

    if jump and s.ljump != s.lljump or not s.ljump:
        s.pitch = s.yaw = s.roll = 0

    if min(0.18, s.dT + 0.05) < s.airtime and s.fz > 100:
        jump = not s.ljump

    return jump


def pre_dodge_handler(s):
    """Handling dodges"""

    jump = 1 if s.poG or s.ljump and not s.poG else 0

    if 0.07 < s.airtime and s.pL[2] > 45:
        s.djT = s.time
        jump = not s.ljump
        exec("s.djl = " + s.djL)
        da = dodge_ang(s, s.djl)
        s.yaw = (abs(Range180(da + 0.5, 1) * 2) - 1)
        s.pitch = Range((abs(da) * 2 - 1) * 2, 1)
        s.roll = 0

    return jump


def flip_handler(s):
    """Handling flip motion after dodge"""

    if 0.05 < s.djtime < 0.25 or (0.25 < s.djtime < 0.65 and abs(s.sa) > 0.5):
        s.pitch = s.yaw = s.roll = 0


def dodge_ang(s, tL):
    """Angle used for dodge, takes into account yaw only"""
    L = tL - s.pL
    yaw = Range180(s.pR[1] - U90, U180) * PI / U180
    x, y = rotate2D(L[0], L[1], -yaw)
    a = math.atan2(y, x)
    return Range180(a / PI - 0.5, 1)
