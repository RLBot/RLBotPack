from PD import *


def execute(s):
    s.controller(s)


def controls(s):
    """Calculate controls"""

    s.handbrake = 0

    slow_down(s)

    s.forwards = s.forwards if abs(s.x) > 120 else s.y > 0
    s.dspeed = math.copysign(s.dspeed, sign(s.forwards))
    s.steer = steer_point(s.sa, s.av)
    s.throttle = throttle_velocity(s.pyv, s.dspeed, s.lthrottle)
    s.boost = to_boost(s) and boost_velocity(s.pyv, s.dspeed, s.lboost)

    s.yaw = yaw_point(s.a, s.av)
    s.pitch = pitch_point(s.i, s.iv)
    s.roll = roll_point(s.r, s.rv) * (abs(s.a) < 0.2)

    turn_around(s)

    jump_and_dodge(s)


def jump_and_dodge(s):

    if to_shoot(s) and s.shoot:

        if to_jump(s):
            s.jumper = 1

        if to_dodge(s):
            s.dodge = 1
            s.djL = "(s.tL + s.bL) / 2"

    if to_flip(s) and s.flip:
        s.dodge = 1
        s.djL = "s.tLs"

    s.jump = jump_handler(s) if s.jumper and s.jcount > 0 else 0

    if s.dodge and s.jcount > 0:
        s.jump = pre_dodge_handler(s)

    wavedash(s)

    flip_handler(s)

    if s.poG and s.lljump != s.ljump:
        s.jump = s.ljump

    if s.poG and s.lpoG and s.jump and s.ljump and s.lljump and s.counter % 10 == 1:
        s.jump = 0


def to_shoot(s):
    """Conditions to shoot"""
    if s.kickoff or (not s.behind and (abs(s.glinex) < 1100 or Range180(s.gta - s.gpa, 1) < 0.1 or 1)):
        return 1
    if (s.behind or abs(s.a) > .8) and abs(s.oglinex) > 1400:
        return 1
    return 0


def to_dodge(s):
    """Condidtions to dodge"""
    if abs(s.pL[2] - s.tL[2]) < 110 and s.jcount > 0 and (s.gtime > 0.05 or not s.poG):

        if s.fgd2 < 140 and s.dT < .35:
            return 1

        if s.fgd2 < 250 and s.dT < .35 and s.pvd < 300:
            return 1

    return 0


def to_jump(s):
    """Conditions to jump"""

    s.zspeed = s.z / (s.dT + 1e-3)
    s.jumpd = min(s.dT * 290, s.jcount * 200)
    s.boostd = 0.5 * 991 * min(s.dT - .5, s.pB / 33) ** 2
    boostd = max(s.boostd - s.jumpd, 1)

    if s.fd2 < 120 + boostd / 2 and 99 < s.fz < 99 + s.jumpd + boostd / 2 and s.jcount > 0 and s.tL[2] > 110:
        if 150 < s.zspeed < 400 + max(s.boostd - 400, 0) / max(s.dT - .5, .01):
            return 1

        if abs(s.dT - s.fz / 300) < .05:
            return 1

    if s.fd2 < 150 and 100 < s.z < s.jcount * 220 + 80:
        if s.d2 < 140 and s.vd2 < 180:
            return 1

    return 0


def to_flip(s):
    """Conditions to flip"""

    if s.poG and s.gtime > 0.05 and not s.jumper and ang_dif(s.sa, s.pva, 1) < .06:

        if s.sd > min(s.pvd + 400, 2300) * (.8 + .4 * (abs(s.sa) < 0.5)) and s.pvd < abs(s.dspeed) - 450:

            if s.pB < 80 and s.pyv > 1640 or (s.pyv > 1120 and s.pB < 16) or (s.pyv > 960 and s.pB < 5):
                if abs(s.pfL[2] - s.tL[2]) < 150:
                    return 1

            # backflip
            if abs(s.a) > 0.75 and s.pyv < 99:
                return 1

    return 0


def slow_down(s):
    """Lower speed if target is inside our turning circle"""

    if s.poG:
        lpcL = a3([s.prd * sign(s.sx), -50, 0])
        cdist = dist2d(lpcL, [s.sx, s.sy])
        s.thspeed = Range((s.sd) / (s.dT + 1e-4) + s.poG * 250 * s.dT, 2310)
        if max(abs(s.z), abs(s.bz)) > 130 and abs(s.x) < 120:
            s.dspeed = Range(s.thspeed, s.dspeed)

        if s.poG and cdist < s.prd or 1:
            turnspeed = max(turning_speed(min(local_radius(s.sx, s.sy), 1170)), 250)
            if abs(s.x) > 130:
                s.dspeed = Range(turnspeed, s.dspeed)
            # if we're already too slow : handbrake
            if to_handbrake(s):
                s.handbrake = 1


def turn_around(s):
    """Turn around from facing backwards"""
    if s.poG and s.d2 > 750 and abs(s.sa + s.av / 3) > 0.45:
        if s.pyv < -400:
            if abs(s.sa) > 0.98:
                s.steer = 1
            if (abs(s.sa) < 0.98 and abs(s.av) > 0.5 and ang_dif(s.sa, s.pva, 1) < .25):
                s.handbrake = 1
            s.steer = -sign(s.steer)

    # # three point turn
    # if (s.poG and 20 < abs(s.sx) < 400 and abs(s.sy) < 200 and .35 < abs(s.sa) < .65 and
    #         abs(s.pyv) < 550 and dist3d(s.pV, s.tV) < 550):
    #     s.throttle = -sign(s.throttle)
    #     s.steer = -sign(s.steer)


def wavedash(s):
    """Conditions to wavedash"""
    if (s.jcount > 0 and s.pL[2] + s.pV[2] / 20 < 32 and abs(s.r) < 0.1 and abs(s.sa) < 0.04 and s.sy > 400 and
            0 < abs(s.pR[0] / PI) < 0.12 and not s.poG and s.pV[2] < -210):
        # Forward wavedash
        s.jump = not s.ljump
        s.pitch = -1
        s.yaw = s.roll = 0


def to_handbrake(s):
    """Condition to handbrake"""

    if .2 < ang_dif(s.sa, s.av / 9, 1) < .8 and s.av * s.steer >= 0 and s.pyv * s.throttle >= 0 and abs(s.pxv) < 500:
        return 1

    if ang_dif(s.sa, s.pva, 1) < .15 and .15 < abs(s.sa) < .85:
        return 1

    return 0


def to_boost(s):
    """Condition to boost"""
    return s.throttle == 1 and s.pB > 1 and (abs(s.a) < .1 and abs(s.i) < .1 or s.poG)


def jump_handler(s):
    """Handling single and double jumps"""

    jump = 1 if s.poG or s.ljump and not s.poG and s.fz > 0 else 0

    if min(0.19, s.dT + 0.05) < s.airtime and s.fz > 120 and s.jcount:
        jump = not s.ljump
        s.pitch = s.yaw = s.roll = 0

    return jump


def pre_dodge_handler(s):
    """Handling dodges"""

    jump = 1 if s.poG or s.ljump and not s.poG else 0

    if 0.07 < s.airtime and s.pL[2] > 50:
        s.djT = s.time
        jump = not s.ljump
        exec("s.djl = " + s.djL)
        da = dodge_ang(s, s.djl)
        s.yaw = abs(Range180(da + 0.5, 1) * 2) - 1
        s.pitch = abs(da) * 2 - 1
        s.roll = 0

    return jump


def flip_handler(s):
    """Handling flip motion after dodge"""

    if 0.05 < s.djtime < 0.25 or 0.25 < s.djtime < 0.65 and abs(s.a) > 0.5:
        s.pitch = s.yaw = s.roll = 0


def dodge_ang(s, tL):
    """Angle used for dodge, takes into account yaw only"""
    L = tL - s.pL
    yaw = Range180(s.pR[1] - PI / 2, PI)
    x, y = rotate2D(L[0], L[1], -yaw)
    a = math.atan2(y, x)
    return Range180(a / PI - 0.5, 1)
