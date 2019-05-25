from util import *
from Handling import controls
from car_path import min_travel_time
from behavior.ball_chase import aimBias, aimBiasC


def PickupBoost(s):

    s.controller = controls
    s.tL, s.tV, s.taV, s.dT = s.bL, s.bV, s.baV, s.pdT

    boost_pad = closest_available_boost(s.pL * .7 + .3 * s.ogoal, s.large_pads)
    if boost_pad is None:
        boost_pad = closest_available_boost(s.pL, s.small_pads)
        if boost_pad is None:
            print("No boost pads available?!")
            boost_pad = s.large_pads[0]

    # s.tLb = set_dist(s.tL, s.ogoal, 105)
    s.tLb = boost_pad.pos

    s.fx, s.fy, s.fz = local(s.tL, s.pfL, s.pR)
    s.fd, s.fa, s.fi = spherical(s.fx, s.fy, s.fz)
    s.fd2 = dist2d([s.fx, s.fy])
    s.fgd2 = dist2d(s.pfL, s.tL)

    s.r = s.pR[2] / PI

    aimBias(s, s.tLb, s.ogoal)
    aimBiasC(s)

    s.x, s.y, s.z = local(s.tLs, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    s.dspeed = 2300
    s.forwards = 1

    s.tLs = boost_pad.pos
    s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)
    s.tt = min_travel_time(s.sd * (1 + abs(s.sa)), s.pyv, s.pB)
    s.ott = min_travel_time(dist3d(s.tLs, s.oL), dist3d(s.oV), s.oB)

    s.txv, s.tyv, s.tzv = s.bxv, s.byv, s.bzv
    s.xv, s.yv, s.zv = s.pxv - s.txv, s.pyv - s.tyv, s.pzv - s.tzv
    s.vd, s.va, s.vi = spherical(s.xv, s.yv, s.zv)
    s.vd2 = dist2d([s.xv, s.yv])

    s.shoot = True
    s.flip = True


def closest_available_boost(my_pos, boost_pads: list):
    """ Returns the closest available boost pad to my_pos"""
    closest_boost = None
    for boost in boost_pads:
        distance = dist3d(boost.pos, my_pos)
        if boost.is_active or distance / 2300 > 10 - boost.timer:
            if closest_boost is None:
                closest_boost = boost
                closest_distance = dist3d(closest_boost.pos, my_pos)
            else:
                if distance < closest_distance:
                    closest_boost = boost
                    closest_distance = dist3d(closest_boost.pos, my_pos)
    return closest_boost
