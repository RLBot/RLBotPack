from util import *
import PhysicsLib

from behavior.kickoff import ChaseKickoff
from behavior.ball_chase import ChaseBallBias, aimBias, aimBiasC
from behavior.pickup_boost import PickupBoost
from car_path import min_travel_time

from rlbot.utils.structures.quick_chats import QuickChats

from copy import deepcopy


def plan(s):
    """Decide objectif."""

    GatherInfo(s)

    if s.kickoff:
        ChaseKickoff(s)
    else:

        if not hasattr(s, 'in_prog'):
            s.in_prog = False
            s.state = None
            s.in_prog2 = False

        if hasattr(s, 'large_pads') and s.large_pads:

            if s.pB == 100 or dist3d(s.ogoal, s.ptL) < 2000:
                s.in_prog = False
                s.state = None

            if s.in_prog and s.state is not None:
                s.state(s)
                # print(s.state.__name__)
                return

            ttog = dist3d(s.ogoal, s.bL) / max(s.bV.dot(normalize(s.ogoal - s.bL)), 1)
            ttogaoh = s.odT + dist3d(s.otL, s.ogoal) / 6000

            if not s.aerialing and s.pB < 18 and not s.obehind and s.active and not s.in_prog:
                PickupBoost(s)
                ttprog = min_travel_time(dist3d(s.tLs, s.ogoal) * 1.1, s.pyv, 64) + s.tt
                safe = ttprog + .2 < min(ttog, ttogaoh)
                if safe and s.tt < s.ott:
                    s.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_NeedBoost)
                    s.in_prog = True
                    s.state = PickupBoost
                    return

        ChaseBallBias(s)

        if abs(s.G) > 99:

            blockable = min(abs(s.oglinex), abs(s.obglinex)) < 1500 and s.infront or dist3d(s.ogoal, s.ptL) < 3500

            odt_adv = s.pdT - s.odT
            pdt_adv = -odt_adv
            if odt_adv > .5 and s.bV.dot(s.ogoald) > 300 and not blockable and not s.in_prog2:
                s.in_prog2 = True
                # s.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Apologies_Cursing)

            if s.in_prog2:

                n = 0.85
                ogoal = deepcopy(s.ogoal) * n
                loc = set_dist(s.tL, ogoal, min(dist3d(s.tL, ogoal), 3500))
                direction = mid_vect(s.tL - loc, s.pL - loc)
                direction *= np.array([1, 1, 0])

                if pdt_adv > .5 or dist3d(s.ogoal, s.ptL) < 1500 or s.bV.dot(s.ogoald) < - 300 or dist3d(s.pL, loc) < 999:
                    s.in_prog2 = False
                    # s.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Information_Incoming)
                    return

                aimBias(s, loc, loc + direction)
                aimBiasC(s)

                s.tLs[2] = 0

                s.sx, s.sy, s.sz = local(s.tLs, s.pL, s.pR)
                s.sd, s.sa, s.si = spherical(s.sx, s.sy + 50, s.sz)
                s.a, s.i = s.sa, s.si
                s.pB = 0

                s.dspeed = 2310
                s.flip = True


def GatherInfo(s):
    """Gather necessary info"""

    min_speed = 1400 if s.pB > 30 else 999
    min_speed = ((2300 - s.pvd) + dist3d(s.pV, s.bV)) * abs(s.ba) * 2 + 100

    # Opponent info

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.oL, s.oV, s.obd / min_speed, 30, g=s.G)

    s.otL = a3(iState.Ball.Location)
    s.otV = a3(iState.Ball.Velocity)
    s.ofL = a3(iState.Car.Location)
    s.odT = iState.dt

    s.ofd = dist3d(s.otL, s.ofL)
    s.odT += s.ofd / (dist3d(s.oV) * 0.5 + 0.5 * 2300)
    s.otL[1] = Range(s.otL[1], abs(s.ogoal[1]))

    s.ooglinex = line_intersect(([0, s.ogoal[1]], [1, s.ogoal[1]]), (s.ofL * .5 + .5 * s.oL, s.otL))[0]

    # s.obd = dist3d(s.oL, s.bL)
    s.obfd = dist3d(s.ofL, s.otL)

    # player info

    s.prd = turning_radius(s.pvd)

    iState = PhysicsLib.intercept2(s.bL, s.bV, s.baV, s.pL, s.pV, s.bd / min_speed, 60, g=s.G)

    s.ptL = a3(iState.Ball.Location)
    s.ptV = a3(iState.Ball.Velocity)
    s.ptaV = a3(iState.Ball.AngularVelocity)
    s.pfL = a3(iState.Car.Location)
    s.pfV = a3(iState.Car.Velocity)
    s.pdT = iState.dt

    s.pfd = dist3d(s.pfL, s.ptL)
    s.pdT += s.pfd / (s.pvd * 0.5 + 0.5 * 2300)
    s.otL[1] = Range(s.ptL[1], abs(s.ogoal[1]))

    s.glinex = line_intersect(([0, s.goal[1]], [1, s.goal[1]]), (s.pL, s.ptL))[0]

    s.oglinex = line_intersect(([0, s.ogoal[1]], [1, s.ogoal[1]]), (s.pL, s.ptL))[0]

    s.obglinex = line_intersect(([0, s.ogoal[1]], [1, s.ogoal[1]]),
                                ([s.bL[0], s.bL[1]], [s.bL[0] + s.bV[0], s.bL[1] + s.bV[1]]))[0]

    # goal location related

    s.gaimdx = abs(s.goal[0] - s.glinex)

    s.gtL = s.ptL - s.goal
    s.gpL = s.pL - s.goal

    s.gtd, s.gta, s.gti = spherical(*s.gtL, 0)
    s.gpd, s.gpa, s.gpi = spherical(*s.gpL, 0)

    s.gtd = dist3d(s.goal, s.ptL)
    s.gpd = dist3d(s.goal, s.pL)
    s.ogtd = dist3d(s.ogoal, s.ptL)
    s.ogpd = dist3d(s.ogoal, s.pL)

    s.o_gtd = dist3d(s.ogoal, s.otL)
    s.o_gpd = dist3d(s.ogoal, s.oL)
    s.o_ogtd = dist3d(s.goal, s.otL)
    s.o_ogpd = dist3d(s.goal, s.oL)

    # TODO: shot angle possible

    # game state info

    s.aerialing = not s.poG and (s.airtime > .2 and s.pL[2] + s.pV[2] / 2 > 150 or s.jumper)
    s.behind = s.gpd < s.gtd or s.ogpd > s.ogtd
    s.offense = s.gpd > s.gtd or dist3d(s.ptL, s.goal) < 3500
    s.infront = s.ptL[1] * s.color + 90 > s.pL[1] * s.color

    s.obehind = s.o_gpd < s.o_gtd or s.o_ogpd > s.o_ogtd

    s.kickoff = not s.bH and dist3d(s.bL) < 99
