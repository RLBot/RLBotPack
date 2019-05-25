from util import *
import PhysicsLib
import Physics as Ph
from PD import tfs


def plan(s):
    """Decide objectif."""

    GatherInfo(s)

    ChaseBallBias(s)


def GatherInfo(s):
    """Gather necessary info"""

    min_speed = 800

    # player info

    s.prd = turning_radius(s.pvd)

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.pL, s.pV, s.bd / min_speed, 60)

    s.ptL = a3(iState.Ball.Location)
    s.ptV = a3(iState.Ball.Velocity)
    s.ptaV = a3(iState.Ball.AngularVelocity)
    s.pfL = a3(iState.Car.Location)
    s.pfV = a3(iState.Car.Velocity)
    s.pdT = iState.dt

    s.bfd = dist3d(s.pfL, s.ptL)

    s.glinex = line_intersect(([0, Ph.wy * s.color], [1, Ph.wy * s.color]),
                              ([s.pL[0], s.pL[1]], [s.ptL[0], s.ptL[1]]))[0]

    s.glinez = line_intersect(([0, Ph.wy * s.color], [1, Ph.wy * s.color]),
                              ([s.pL[2], s.pL[1]], [s.ptL[2], s.ptL[1]]))[0]

    s.oglinex = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                               ([s.pL[0], s.pL[1]], [s.ptL[0], s.ptL[1]]))[0]

    # s.oglinez = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
    #                            ([s.pL[2], s.pL[1]], [s.ptL[2], s.ptL[1]]))[0]

    # Opponent info

    s.obd = dist3d(s.oL, s.bL)

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.oL, s.oV, s.obd / min_speed, 30)

    s.otL = a3(iState.Ball.Location)
    s.otV = a3(iState.Ball.Velocity)
    s.ofL = a3(iState.Car.Location)
    s.odT = iState.dt

    s.ofd = dist3d(s.otL, s.ofL)

    # s.obd = dist3d(s.oL, s.bL)
    s.obfd = dist3d(s.ofL, s.otL)

    s.ooglinex = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                                ([s.oL[0], s.oL[1]], [s.otL[0], s.otL[1]]))[0]

    s.ooglinez = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                                ([s.oL[2], s.oL[1]], [s.otL[2], s.otL[1]]))[0]

    # other

    s.goal = a3([-Range(s.glinex, 600) / 2, max(Ph.wy, abs(s.ptL[1]) + 1) * s.color, 300])

    s.ogoal = a3([Range(s.ooglinex * .8, 900), -max(Ph.wy, abs(s.ptL[1]) + 1) * s.color, 300])

    s.gaimdx = abs(s.goal[0] - s.glinex)
    s.gaimdz = abs(s.goal[2] - s.glinez)

    s.gx, s.gy, s.gz = local(s.goal, s.pL, s.pR)
    s.gd, s.ga, s.gi = spherical(s.gx, s.gy, s.gz)

    s.ogx, s.ogy, s.ogz = local(s.ogoal, s.pL, s.pR)
    s.ogd, s.oga, s.ogi = spherical(s.ogx, s.ogy, s.ogz)

    s.gtL = s.ptL - s.goal
    s.gpL = s.pL - s.goal

    s.gtd, s.gta, s.gti = spherical(*s.gtL, 0)
    s.gpd, s.gpa, s.gpi = spherical(*s.gpL, 0)

    s.gtd = dist3d(s.goal, s.ptL)
    s.gpd = dist3d(s.goal, s.pL)
    s.ogtd = dist3d(s.ogoal, s.ptL)
    s.ogpd = dist3d(s.ogoal, s.pL)

    # States

    s.aerialing = not s.poG and s.pL[2] > 150 and s.airtime > .25
    s.kickoff = not s.bH and dist3d(s.bL) < 99
    s.offense = s.ogtd + 70 > s.ogpd
    s.behind = s.gpd < s.gtd or s.ogpd > s.ogtd


def ChaseBallBias(s):

    s.tL, s.tV, s.taV, s.dT = s.ptL, s.ptV, s.ptaV, s.pdT

    dt = s.bfd / 5300
    tPath = PhysicsLib.predictPath(s.ptL, s.ptV, s.ptaV, dt + 1 / 60, 60)
    tState = tPath.ballstates[min(tPath.numstates - 1, 0)]
    s.tL = a3(tState.Location)
    s.tV = a3(tState.Velocity)
    s.pfL, s.pfV = PhysicsLib.CarStep(s.pfL, s.pfV, dt)
    s.dT += dt

    s.fx, s.fy, s.fz = local(s.tL, s.pfL, s.pR)
    s.fd, s.fa, s.fi = spherical(s.fx, s.fy, s.fz)
    s.fd2 = dist2d([s.fx, s.fy])
    s.fgd2 = dist2d(s.pfL, s.tL)

    s.tx, s.ty, s.tz = local(s.tL, s.pL, s.pR)
    s.td, s.ta, s.ti = spherical(s.tx, s.ty, s.tz)
    s.td2 = dist2d([s.tx, s.ty])
    s.r = s.pR[2] / U180
    s.tLb = s.tL

    Cl = Ph.Collision_Model(s.pfL)
    if s.aerialing and not Cl.hasCollided:
        n1 = normalize(s.tL - s.pL)
        v1 = s.pV
        b1 = v1 - np.dot(v1, n1) * n1
        d = s.bd
        v = max(s.pvd * .5 + .5 * dist3d(s.pfV), 200)
        t = d / v
        s.tLb = s.tL - b1 * t

    s.ax, s.ay, s.az = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.ax, s.ay, s.az)
    s.d2 = dist2d([s.ax, s.ay])

    s.tLs = s.tL

    if s.pL[2] > 20 and s.poG and (s.tL[2] < s.az or s.az > 450 + s.pB * 9):
        s.tLs[2] = 50

    s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)
    s.sd2 = dist2d([s.ax, s.ay])

    if not s.offense:
        s.goal = set_dist(s.tL, s.ogoal, -999)

    if max(abs(s.fz), abs(s.bz)) > 130 or s.odT + dist3d(s.otL, s.ofL) / 5300 < s.pdT + 1 or 1:
        Bias(s, 93)
    else:
        aimBias(s, s.goal)

    s.txv, s.tyv, s.tzv = s.bxv, s.byv, s.bzv
    s.xv, s.yv, s.zv = s.pxv - s.txv, s.pyv - s.tyv, s.pzv - s.tzv
    s.vd, s.va, s.vi = spherical(s.xv, s.yv, s.zv)
    s.vd2 = dist2d([s.xv, s.yv])


def Bias(s, R, BC=1):

    if s.pL[1] * s.color < -(Ph.wy + R):
        R = 0

    s.tLb = set_dist(s.ptL, s.goal, -R)
    if s.behind:
        s.tLb = s.ptL + mid_vect(s.ogoal - s.ptL, s.pL - s.ptL) * R

    s.x, s.y, s.z = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    lptL = local(s.ptL, s.pL, s.pR)
    ltLb = np.array([s.x, s.y, s.z])

    if BC:
        bxc = box_collision(lptL - ltLb)
        ltLb -= bxc * abs(bxc[0]) >= HITBOX[0]

    ltLb[1] += 30
    s.sx, s.sy, s.sz = ltLb
    s.sd, s.sa, s.si = spherical(*ltLb)


def mid_vect(v1, v2):
    return normalize((normalize(v1) + normalize(v2)) / 2)


def aimBias(s, goal, bR=92):
    """Offset target location for goal shooting"""

    s.prd = (turning_radius(s.pvd) * .5 + .5 * 340)
    s.trd = s.prd
    s.dspeed = 2300

    # s.trd = 105
    r = 93 + 20
    tLb = set_dist(s.ptL, goal, -r)

    s.x, s.y, s.z = local(tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    lpcL, ltcL, lpcTL, ltcTL, td, s.forwards = shootingPath(s.ptL, s.pL, s.pR, s.trd, s.prd, goal, s.pyv, r)

    s.tcL = world(ltcL, s.pL, s.pR)
    s.pcL = world(lpcL, s.pL, s.pR)
    s.pcTL = world(a3([*lpcTL, lpcL[2]]), s.pL, s.pR)
    s.tcTL = world(a3([*ltcTL, ltcL[2]]), s.pL, s.pR)
    s.tLb = set_dist(s.ptL, s.goal, -92)

    if dist2d(ltcL) > s.trd + 50:
        if dist2d(ltcTL, [0, 55]) > 150:
            tLb = s.tcTL

    if dist2d([s.x, s.y]) < 150:
        tLb = s.tLb

    s.sx, s.sy, s.sz = local(tLb, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy, s.sz)


def shootingPath(tL, pL, pR, trd, prd, goal, pyv, bR=92):

    tLb = set_dist(tL, goal, -bR)

    ltL = local(tL, pL, pR)
    ltLb = local(tLb, pL, pR)

    path = None
    for t in range(2):
        ltcL = set_dist_ang(ltLb, ltL, trd, PI / 2 * sign(t))
        for p in range(2):
            f = sign(pyv)
            lpcL = a3([prd * sign(p) * sign(f), 55, 0])
            lpcTL, ltcTL = circles_tangent(lpcL, prd, -sign(p), ltcL, trd, -sign(t))
            pca = abs(relative_angle(lpcTL, [0, 55], lpcL))
            tca = Range360(relative_angle(ltcTL, ltLb, ltcL) * sign(t), PI)
            td = pca * prd + dist2d(lpcTL, ltcTL) + tca * trd + (sign(f) != sign(pyv)) * abs(pyv) * tfs(pyv) * 2
            if path is None or td < path[4]:
                path = [lpcL, ltcL, lpcTL, ltcTL, td, f]

    return path
