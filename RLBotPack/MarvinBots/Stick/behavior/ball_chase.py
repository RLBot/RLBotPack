from util import *
from car_path import shootingPath
from Handling import controls
from PhysicsLib import predict_CarLoc
from copy import deepcopy

BR = 105


def ChaseBallBias(s):

    s.controller = controls
    s.tL, s.tV, s.taV, s.dT = s.ptL, s.ptV, s.ptaV, s.pdT
    s.dspeed = 2300
    s.r = s.pR[2] / PI
    s.forwards = 1

    goal = deepcopy(s.goal)
    goal[1] = (max(abs(s.ptL[1]), abs(goal[1])) + 90) * sign(goal[1])
    goal[0] = -sign(s.glinex) * 300

    if dist3d(s.ogoal, s.tL) < 2500 or not s.infront:
        ogoal = deepcopy(s.ogoal)
        ogoal[0] = Range(s.tL[0], 999)
        direction = -mid_vect(s.pL - s.tL, ogoal - s.tL)
        direction *= np.array([1, 0.0, 0.5])
        goal = direction * 3999 + s.tL
        s.prd = 1

    s.tLb = set_dist(s.tL, goal, -BR)
    s.tLs = s.tLb

    if s.aerialing:

        i = 2
        step = 6

        bp = s.get_ball_prediction_struct()

        while i < min(bp.num_slices - 1, 360):

            bs = bp.slices[i]
            s.tL = a3v(bs.physics.location)
            s.tV = a3v(bs.physics.velocity)
            s.dT = bs.game_seconds - s.time

            tLb2 = set_dist(s.tL, goal, -BR)
            tLb = tLb2 - s.pV * s.dT - 0.5 * a3l([0, 0, s.G]) * s.dT * s.dT
            ltLb = local(tLb, s.pL, s.pR)
            stLb = spherical(*ltLb)

            phi = abs(stLb[1]) + abs(stLb[2])
            T = 0.7 * (2.0 * math.sqrt(phi / 9))
            bt = max(s.dT - T, .01)

            bd = 0.5 * 991 * bt ** 2
            if abs(bd - dist3d(tLb - s.pL)) < 99:
                break

            B_avg = 2.0 * dist3d(tLb - s.pL) / (bt ** 2)
            if 0 <= B_avg < 1000:
                break

            if abs(s.tL[1]) > abs(s.ogoal[1]):
                break

            i += step

        if s.dT - T < s.pB / 33 + .2:
            s.tLb = tLb
            s.dspeed = 2300
            s.pfL = s.pL + s.pV * s.dT * 0.5 * s.G * s.dT ** 2
            if s.pfd < 80:
                s.tLb = set_dist(s.ptL, goal, -BR)
                s.pB = 0
        elif s.pB != 100:
            s.pB = 0

    if s.pL[2] < 90 and s.poG:

        bp = s.get_ball_prediction_struct()
        i = 1
        step = 5

        ttotal = 0

        while i < min(bp.num_slices - 1, 360):

            bs = bp.slices[i]
            s.tL = a3v(bs.physics.location)
            s.tV = a3v(bs.physics.velocity)
            s.dT = bs.game_seconds - s.time

            s.tLb = set_dist(s.tL, goal, -BR)
            ltLb = local(s.tLb, s.pL, s.pR)

            s.zspeed = ltLb[2] / (s.dT + 1e-4)
            s.jumpd = min(s.dT * 300, s.jcount * 220)
            s.boostd = 0.5 * 991 * min(s.dT - .5, s.pB / 33) ** 2
            boostd = max(s.boostd - s.jumpd, 1)
            b = 1 < s.zspeed < 400 + boostd / max(s.dT - .5, .01)

            if (ltLb[2] < 150 + b * s.jcount * 180 + boostd / 2 or s.tL[2] < 140) or abs(s.tL[1]) > abs(s.ogoal[1]):
                # if (ltLb[2] < 150 or s.tL[2] < 140):

                aimBias(s, s.tL, goal, BR)
                ttotal = max(-1 + math.sqrt(s.td / 500), 1 / 30)
                ttotal = s.tt * .8 + .2 * ttotal

                if ttotal < s.dT:
                    break

            i += step

        if ttotal != 0:
            aimBiasC(s)

    s.pfL = predict_CarLoc(s.pL, s.pV, s.dT, 1 / 20, g=s.G)
    s.fx, s.fy, s.fz = local(s.tL, s.pfL, s.pR)
    s.fd, s.fa, s.fi = spherical(s.fx, s.fy, s.fz)
    s.fd2 = dist2d([s.fx, s.fy])
    s.fgd2 = dist2d(s.pfL, s.tL)

    s.x, s.y, s.z = local(s.tLb, s.pL, s.pR)
    s.d, s.a, s.i = spherical(s.x, s.y, s.z)
    s.d2 = dist2d([s.x, s.y])

    if s.pL[2] > 50 and s.poG and (s.tL[2] < s.z or s.z > 550):
        s.tLs[2] = 0

    if abs(s.pL[1]) > 5150 and s.poG and abs(s.tLs[0]) > 870:
        s.tLs[0] = Range(s.tLs[0], 820)
        s.tLs[1] = Range(s.tLs[1], 5020)

    s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
    s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)

    s.txv, s.tyv, s.tzv = s.bxv, s.byv, s.bzv
    s.xv, s.yv, s.zv = s.pxv - s.txv, s.pyv - s.tyv, s.pzv - s.tzv
    s.vd, s.va, s.vi = spherical(s.xv, s.yv, s.zv)
    s.vd2 = dist2d([s.xv, s.yv])

    if s.poG and (max(abs(s.z), abs(s.fz)) < 130 and max(abs(s.x), abs(s.fx)) < 120):
        s.dspeed = 2300

    s.shoot = s.pdT < s.odT + .2
    s.flip = s.odT > .5 and s.pL[2] < 999

    # s.renderer.begin_rendering(s.index)
    # s.renderer.draw_rect_3d(s.tLb, 7, 7, 1, s.renderer.white(), 1)
    # s.renderer.draw_rect_3d(s.tLs, 8, 8, 1, s.renderer.black(), 1)
    # s.renderer.draw_rect_3d(s.tL, 9, 9, 1, s.renderer.red(), 1)
    # s.renderer.draw_line_3d(s.tL, s.tLb, s.renderer.white())
    # s.renderer.end_rendering()


def aimBias(s, tL, goal, bR=93):
    """Offset target location for goal shooting"""

    s.prd = min(turning_radius(s.pvd), 340)

    # blockable = min(abs(s.oglinex), abs(s.obglinex)) < 1500 and s.infront or dist3d(s.ogoal, s.ptL) < 3500

    if s.poG and s.pL[2] < 99 and abs(s.pL[2] - tL[2]) < 140 and dist3d(s.goal, s.tL) > 1100 and dist3d(s.ogoal, s.ptL) > 2500:
        s.trd = turning_radius(s.pvd)
    else:
        s.trd = 1

    # s.trd = turning_radius(s.pvd)
    s.tspeed = max(turning_speed(s.trd), 250)

    # s.trd = 105
    s.tLb3 = s.tLb2 = set_dist(tL, goal, -bR)
    s.tL2 = tL

    s.lpcL, s.ltcL, s.lpcTL, s.ltcTL, s.td, s.tt, s.forwards = shootingPath(
        tL, s.pL, s.pR, s.trd, s.prd, goal, s.pyv, bR, s.pB)


def aimBiasC(s):
    s.tcL = world(s.ltcL, s.pL, s.pR)
    s.pcL = world(s.lpcL, s.pL, s.pR)
    s.pcTL = world(a3([*s.lpcTL, s.tL2[2]]), s.pL, s.pR)
    s.tcTL = world(a3([*s.ltcTL, s.tL2[2]]), s.pL, s.pR)

    s.dspeed = s.td / (s.dT + .001)

    if dist2d(s.ltcL) > s.trd:
        if dist2d(s.lpcTL, [0, 55]) > 300:
            s.tLb2 = s.pcTL
        if dist2d(s.ltcTL, [0, 55]) > 120 and dist3d(s.tcTL, s.tLb3) > 300:
            s.tLb2 = s.tcTL
            if s.ltcTL[1] / (s.pyv + 1) < abs(s.tspeed - s.pyv) / 3600:
                s.dspeed = min(s.tspeed, s.dspeed)

    if dist3d(s.pL, s.tLb3) < 300:
        s.tLb2 = s.tLb3

    s.tLs = s.tLb2


def convert_shooting_path(f):
    def fnew(*args):
        p = f(*args)
        return [p.player_circle, p.target_circle, p.player_tangent, p.target_tangent, p.total_distance, p.total_time,
                p.forwards]
    return fnew


shootingPath = convert_shooting_path(shootingPath)
