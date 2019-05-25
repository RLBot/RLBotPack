from util import *
from Handling import controls


def ChaseKickoff(s):

    s.controller = controls
    s.tL, s.tV, s.taV, s.dT = s.bL, s.bV, s.baV, s.pdT

    s.tLb = set_dist(s.bL, s.ogoal, 109)

    s.fx, s.fy, s.fz = local(s.tL, s.pfL, s.pR)
    s.fd, s.fa, s.fi = spherical(s.fx, s.fy, s.fz)
    s.fd2 = dist2d([s.fx, s.fy])
    s.fgd2 = dist2d(s.pfL, s.tL)

    s.r = s.pR[2] / PI

    s.x, s.y, s.z = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    s.dspeed = min(max(dist3d(s.oV) + 300, 1400), 2300)
    if s.odT < .14 and s.oL[2] < 19:
        s.jumper = 1
    s.forwards = 1

    s.tLs = s.tLb
    s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)

    s.txv, s.tyv, s.tzv = s.bxv, s.byv, s.bzv
    s.xv, s.yv, s.zv = s.pxv - s.txv, s.pyv - s.tyv, s.pzv - s.tzv
    s.vd, s.va, s.vi = spherical(s.xv, s.yv, s.zv)
    s.vd2 = dist2d([s.xv, s.yv])

    s.shoot = True
    s.flip = False
