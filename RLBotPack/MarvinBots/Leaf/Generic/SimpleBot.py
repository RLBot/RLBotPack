from PD import *
from Physics import wy


def GeneralInfo(s):

    s.oglinex = line_intersect(([0, -wy * s.color], [1, -wy * s.color]),
                               ([s.pL[0], s.pL[1]], [s.bL[0], s.bL[1]]))[0]

    s.obglinex = line_intersect(([0, -wy * s.color], [1, -wy * s.color]),
                                ([s.bL[0], s.bL[1]], [s.bL[0] + s.bV[0], s.bL[1] + s.bV[1]]))[0]

    s.gtd = dist3d(s.goal, s.bL)
    s.gpd = dist3d(s.goal, s.pL)
    s.ogtd = dist3d(s.ogoal, s.bL)
    s.ogpd = dist3d(s.ogoal, s.pL)

    s.behind = s.gpd < s.gtd or s.ogpd > s.ogtd
    s.kickoff = not s.bH and dist3d(s.bL) < 99


def GoTo(s, tL):

    s.tL = tL
    s.x, s.y, s.z = local(s.tL, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y + 50, s.z)
    s.d2 = dist2d([s.x, s.y])
    s.r = s.pR[2] / U180

    SimpleControls(s)


def SimpleControls(s):
    """Calculate controls"""

    s.dspeed = 2310
    s.throttle = throttle_point(s.y, s.pyv, True)
    s.boost = to_boost(s) and boost_velocity(s.pyv, s.dspeed, s.lboost)
    s.steer = steer_point(s.a, s.av)

    s.yaw = yaw_point(s.a, s.av)
    s.pitch = pitch_point(s.i, s.iv)
    s.roll = roll_point(s.r, s.rv) * (abs(s.a) < 0.2)

    s.powerslide = to_powerslide(s)

    turn_around(s)

    jump_and_dodge(s)


def jump_and_dodge(s):

    if to_flip(s):
        s.dodge = 1
        s.djL = "s.tL"

    if s.dodge and s.jcount > 0:
        s.jump = pre_dodge_handler(s)

    wavedash(s)

    flip_handler(s)

    if s.poG and s.lljump != s.ljump:
        s.jump = s.ljump


def to_flip(s):
    """Conditions to flip"""

    if (s.gtime > 0.05 or not s.poG) and not s.jumper and ang_dif(s.a, s.pva, 1) < .06:

        if s.d > min(s.pvd, 2300) * (.8 + .4 * (abs(s.a) < 0.5)) and s.pvd < abs(s.dspeed) - 250:

            if s.pB < 80 and s.pyv > 1640 or (s.pyv > 1120 and s.pB < 16) or (s.pyv > 960 and s.pB < 5):
                return 1

            # backflip
            if abs(s.a) > 0.75 and s.pyv < -140:
                return 1

    return 0


def wavedash(s):
    """Conditions to wavedash"""
    if (s.jcount > 0 and s.pL[2] + s.pV[2] / 20 < 32 and abs(s.r) < 0.1 and abs(s.a) < 0.04 and s.y > 400 and
            0 < abs(s.pR[0] / U180) < 0.12 and not s.poG and s.pV[2] < -210):
        # Forward wavedash
        s.jump = not s.ljump
        s.pitch = -1
        s.yaw = s.roll = 0


def turn_around(s):
    """Turn around from facing backwards"""
    if s.poG and s.d2 > 450 and abs(s.a + s.av / 3) > 0.45:

        if abs(s.a) > 0.98:
            s.steer = 1

        if s.d2 > 600 and s.pyv < -90:
            if (abs(s.a) < 0.98 and abs(s.av) > 0.5 and ang_dif(s.a, s.pva, 1) < .25):
                s.powerslide = 1
            s.steer = -sign(s.steer)

        elif s.d2 > 800 and abs(s.a) < 0.95 and s.pyv < 1000:
            s.throttle = 1

    # three point turn
    if (s.poG and 20 < abs(s.x) < 400 and abs(s.y) < 200 and .35 < abs(s.a) < .65 and
            abs(s.pyv) < 550 and s.pvd < 550):
        s.throttle = -sign(s.throttle)
        s.steer = -sign(s.steer)


def to_powerslide(s):
    """Condition to powerslide"""

    if (.2 < ang_dif(s.a, s.av / 7, 1) < .8 and s.av * s.steer >= 0 and s.pyv * s.throttle >= 0 and
            abs(s.pxv) < 500 and .05 < abs(s.a) < .95):
        return 1

    if ang_dif(s.a, s.pva, 1) < .15 and .1 < abs(s.a) < .9:
        return 1

    return 0


def to_boost(s):
    """Condition to boost"""
    return s.throttle == 1 and (abs(s.a) < .13 and abs(s.i) < .15 or s.poG)


def pre_dodge_handler(s):
    """Handling dodges"""

    jump = 1 if s.poG or s.ljump and not s.poG else 0

    if 0.07 < s.airtime and s.pL[2] > 45:
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
    yaw = Range180(s.pR[1] - U90, U180) * PI / U180
    x, y = rotate2D(L[0], L[1], -yaw)
    a = math.atan2(y, x)
    return Range180(a / PI - 0.5, 1)
