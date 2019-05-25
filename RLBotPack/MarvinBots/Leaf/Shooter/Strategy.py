from util import *
import PhysicsLib
import Physics as Ph
import PD


def plan(s):
    """Decide objectif."""

    GatherInfo(s)
    ChaseBallBias(s)


def GatherInfo(s):
    """Gather necessary info"""

    min_speed = 1400 if s.pB > 30 else 999
    min_speed = ((2300 - s.pvd) + dist3d(s.pV, s.bV)) * abs(s.ba) * 2 + 100

    # Opponent info

    s.obd = dist3d(s.oL, s.bL)

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.oL, s.oV, s.obd / min_speed, 15)

    s.otL = a3(iState.Ball.Location)
    s.otV = a3(iState.Ball.Velocity)
    s.ofL = a3(iState.Car.Location)
    s.odT = iState.dt

    s.ofd = dist3d(s.otL, s.ofL)

    s.ooglinex = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                                (s.ofL * .8 + .2 * s.oL, s.otL * .8 + .2 * s.bL))[0]

    # s.ooglinez = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
    #                             ([s.ofL[2], s.ofL[1]], [s.otL[2], s.otL[1]]))[0]

    # s.obd = dist3d(s.oL, s.bL)
    s.obfd = dist3d(s.ofL, s.otL)

    # player info

    s.prd = turning_radius(s.pvd)

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.pL, s.pV, s.bd / min_speed, 120)

    s.ptL = a3(iState.Ball.Location)
    s.ptV = a3(iState.Ball.Velocity)
    s.ptaV = a3(iState.Ball.AngularVelocity)
    s.pfL = a3(iState.Car.Location)
    s.pfV = a3(iState.Car.Velocity)
    s.pdT = iState.dt


    s.glinex = line_intersect(([0, Ph.wy * s.color], [1, Ph.wy * s.color]),
                              (s.pfL * .5 + .5 * s.pL, s.ptL * .8 + .2 * s.bL))[0]

    # s.glinez = line_intersect(([0, Ph.wy * s.color], [1, Ph.wy * s.color]),
    #                           ([s.pL[2], s.pL[1]], [s.ptL[2], s.ptL[1]]))[0]

    s.oglinex = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                               (s.pfL * .8 + .2 * s.pL, s.ptL * .8 + .2 * s.bL))[0]

    # s.oglinez = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
    #                            ([s.pfL[2], s.pL[1]], [s.pftL[2], s.ptL[1]]))[0]

    s.bfd = dist3d(s.pfL, s.ptL)

    # goal location related

    s.goal = a3([-Range(s.glinex, 600) / 2, max(Ph.wy, abs(s.ptL[1]) + 1) * s.color, 300])

    s.ogoal = a3([Range(s.ooglinex * .8, 900), -max(Ph.wy, abs(s.ptL[1]) + 1) * s.color, 300])

    # s.gaimdx = abs(s.goal[0] - s.glinex)
    # s.gaimdz = abs(s.goal[2] - s.glinez)

    # s.gx, s.gy, s.gz = local(s.goal, s.pL, s.pR)
    # s.gd, s.ga, s.gi = spherical(s.gx, s.gy, s.gz)

    # s.ogx, s.ogy, s.ogz = local(s.ogoal, s.pL, s.pR)
    # s.ogd, s.oga, s.ogi = spherical(s.ogx, s.ogy, s.ogz)

    s.gtL = s.ptL - s.goal
    s.gpL = s.pL - s.goal

    s.gtd, s.gta, s.gti = spherical(*s.gtL, 0)
    s.gpd, s.gpa, s.gpi = spherical(*s.gpL, 0)

    s.gtd = dist3d(s.goal, s.ptL)
    s.gpd = dist3d(s.goal, s.pL)
    s.ogtd = dist3d(s.ogoal, s.ptL)
    s.ogpd = dist3d(s.ogoal, s.pL)

    # near_post = (gx / 2 * sign(s.bL[0]), s.goal[1])
    # tangent = tangent_point(near_post, R, s.bL, s.color * sign(s.bL[0]))

    # s.x_point = line_intersect([(1, near_post[1]), (-1, near_post[1])], [s.bL, tangent])[0]

    # States

    s.aerialing = not s.poG and s.pL[2] > 150 and s.airtime > .25
    s.kickoff = not s.bH and dist3d(s.bL) < 99
    s.behind = s.gpd < s.gtd or s.ogpd > s.ogtd
    s.offense = s.ogtd + 70 > s.ogpd

    # Other
    s.tLb = set_dist(s.ptL, s.goal, -92)
    s.x, s.y, s.z = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    s.bvglinex = line_intersect(([0, -Ph.wy * s.color], [1, -Ph.wy * s.color]),
                                (s.bL, s.bL + s.bV))[0]


def ChaseBallBias(s):

    s.tL, s.tV, s.taV, s.dT = s.ptL, s.ptV, s.ptaV, s.pdT

    if s.tL[1] * s.color < -Ph.wy - 80:
        s.tL[1] = -Ph.wy * s.color - 80

    s.fx, s.fy, s.fz = local(s.tL, s.pfL, s.pR)
    s.fd, s.fa, s.fi = spherical(s.fx, s.fy, s.fz)
    s.fd2 = dist2d([s.fx, s.fy])
    s.fgd2 = dist2d(s.pfL, s.tL)
    s.r = s.pR[2] / U180

    s.dspeed = 2310
    s.forwards = 1

    goal = s.goal if not s.behind else set_dist(s.tL, s.ogoal, -999)

    s.tLs = aimBias(s, goal) if s.pL[2] < 50 or not s.poG else s.tLb

    s.tLb = set_dist(s.ptL, s.goal, -92)
    s.x, s.y, s.z = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    if s.pL[2] > 20 and s.poG and (s.tL[2] < s.z or s.z > 450 + s.pB * 9):
        s.tLs[2] = 50

    s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)

    s.txv, s.tyv, s.tzv = s.bxv, s.byv, s.bzv
    s.xv, s.yv, s.zv = s.pxv - s.txv, s.pyv - s.tyv, s.pzv - s.tzv
    s.vd, s.va, s.vi = spherical(s.xv, s.yv, s.zv)
    s.vd2 = dist2d([s.xv, s.yv])

    s.shoot = True


def aimBias(s, goal, bR=92):
    """Offset target location for goal shooting"""

    lpcL = a3([s.prd * sign(s.x), 50, 0])
    s.trd = min((s.prd + 340) / 2, dist2d(lpcL, [s.x, s.y]) + 50)
    s.prd = s.trd
    s.tspeed = max(turning_speed(s.trd), 200)

    # s.trd = 105
    r = 93 + 20
    tLb = set_dist(s.tL, goal, -r)

    if s.behind or s.odT < s.pdT + .2:
        goal = normalize(normalize(goal - s.tL) * 0.5 - 0.5 * normalize(s.pL - s.tL)) + s.tL

    lpcL, ltcL, lpcTL, ltcTL, td, tt, s.forwards = shootingPath(s.tL, s.pL, s.pR, s.trd, s.prd, goal, s.pyv, r)

    s.tcL = world(ltcL, s.pL, s.pR)
    s.pcL = world(lpcL, s.pL, s.pR)
    s.pcTL = world(a3([*lpcTL, lpcL[2]]), s.pL, s.pR)
    s.tcTL = world(a3([*ltcTL, ltcL[2]]), s.pL, s.pR)
    s.tLb = set_dist(s.tL, goal, -92)

    if dist2d(ltcL) > s.trd + 50:
        if dist2d(lpcTL, [0, 50]) > 200:
            tLb = s.pcTL
        if dist2d(ltcTL, [0, 50]) > 200:
            tLb = s.tcTL

    if dist2d([s.x, s.y]) < 150:
        tLb = s.tLb

    return tLb


def shootingPath(tL, pL, pR, trd, prd, goal, pyv, bR=92):

    tLb = set_dist(tL, goal, -bR)

    ltL = local(tL, pL, pR)
    ltLb = local(tLb, pL, pR)

    path = None
    for t in range(2):
        ltcL = set_dist_ang(ltLb, ltL, trd, PI / 2 * sign(t))
        for p in range(2):
            for f in range(2):
                lpcL = a3([prd * sign(p) * sign(f), 55, 0])
                lpcTL, ltcTL = circles_tangent(lpcL, prd, -sign(p), ltcL, trd, -sign(t))
                pca = abs(relative_angle(lpcTL, [0, 55], lpcL))
                tca = Range360(relative_angle(ltcTL, ltLb, ltcL) * sign(t), PI)
                td = pca * prd + dist2d(lpcTL, ltcTL) + tca * trd + (sign(f) != sign(pyv)) * abs(pyv) * PD.tfs(pyv) * 2
                pspeed = turning_speed(prd)
                tspeed = turning_speed(trd)
                tt = pca * prd / pspeed + dist2d(lpcTL, ltcTL) / ((pspeed + tspeed) / 2) + tca * trd / tspeed
                if path is None or td < path[4]:
                    path = [lpcL, ltcL, lpcTL, ltcTL, td, tt, f]

    return path
