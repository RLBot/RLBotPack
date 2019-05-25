from util import *
import Physics as Ph


def pre_process(s, game):

    s.game = game
    s.player = game.gamecars[s.index]
    s.ball = game.gameball
    s.info = game.gameInfo

    s.time = s.info.TimeSeconds
    s.bH = s.info.bBallHasBeenHit

    s.pL = a3(s.player.Location)
    s.pR = a3(s.player.Rotation)
    s.pV = a3(s.player.Velocity)
    s.paV = a3(s.player.AngularVelocity)
    s.pJ = s.player.bJumped
    s.pdJ = s.player.bDoubleJumped
    s.poG = s.player.bOnGround
    s.pB = s.player.Boost
    s.pS = s.player.bSuperSonic

    s.bL = a3(s.ball.Location)
    s.bV = a3(s.ball.Velocity)
    s.baV = a3(s.ball.AngularVelocity)

    s.bx, s.by, s.bz = local(s.bL, s.pL, s.pR)
    s.bd, s.ba, s.bi = spherical(s.bx, s.by, s.bz)
    s.iv, s.rv, s.av = local(s.paV, 0, s.pR)
    s.pxv, s.pyv, s.pzv = local(s.pV, 0, s.pR)
    s.pvd, s.pva, s.pvi = spherical(s.pxv, s.pyv, s.pzv)
    s.bxv, s.byv, s.bzv = local(s.bV, 0, s.pR)
    s.bvd, s.bva, s.bvi = spherical(s.bxv, s.byv, s.bzv)

    s.color = -sign(s.player.Team)

    if not hasattr(s, 'counter'):

        s.counter = -1

        s.throttle = s.steer = s.pitch = s.yaw = s.roll = s.jump = s.boost = 0
        s.powerslide = s.ljump = 0

        s.aT = s.gT = s.sjT = s.djT = s.time

        s.dodge = s.jumper = 0

        feedback(s)

    if s.poG and not s.lpoG:
        s.gT = s.time
    if s.lpoG and not s.poG:
        s.aT = s.time

    s.airtime = s.time - s.aT
    s.gtime = s.time - s.gT
    s.djtime = s.time - s.djT

    if s.lljump and not s.ljump or s.airtime > 0.2:
        s.sjT = s.ltime

    s.sjtime = s.time - s.sjT

    if s.poG:
        s.airtime = s.sjtime = s.djtime = 0
    else:
        s.gtime = 0

    if s.poG:
        s.jcount = 2
    elif s.pdJ or (s.sjtime > 1.25 and s.pJ):
        s.jcount = 0
    else:
        s.jcount = 1

    if s.jcount == 0 or s.poG:
        s.dodge = s.jumper = 0

    s.dtime = s.time - s.ltime
    if s.dtime != 0:
        s.fps = 1 / s.dtime
    else:
        s.fps = 0

    oppIndex = not s.index

    if game.numCars > 2:  # use closest opponent to the ball
        oppIndex = -1
        for i in range(game.numCars):
            if game.gamecars[i].Team != s.player.Team:
                if oppIndex == -1 or (dist3d(a3(game.gamecars[i].Location), s.bL) <
                                      dist3d(a3(game.gamecars[oppIndex].Location),
                                             s.bL)):
                    oppIndex = i

    if oppIndex < game.numCars:
        opp = game.gamecars[oppIndex]
        s.oL = a3(opp.Location)
        s.oV = a3(opp.Velocity)
        s.oR = a3(opp.Rotation)
    else:
        s.oL = s.oV = s.oR = np.zeros(3) + 3e3

    s.obd = dist3d(s.bL, s.oL)

    s.goal = a3([0, max(Ph.wy, abs(s.bL[1]) + 1) * s.color, 300])
    s.ogoal = a3([0, -max(Ph.wy, abs(s.bL[1]) + 1) * s.color, 300])
    s.behind = dist3d(s.ogoal, s.pL) > dist3d(s.ogoal, s.bL) or dist3d(s.goal, s.pL) < dist3d(s.goal, s.bL)


def feedback(s):

    s.ltime = s.time
    s.lpoG = s.poG

    s.lljump = s.ljump

    s.lthrottle, s.lsteer = s.throttle, s.steer
    s.lpitch, s.lyaw, s.lroll = s.pitch, s.yaw, s.roll
    s.ljump, s.lboost, s.lpowerslide = s.jump, s.boost, s.powerslide

    s.counter += 1

    if hasattr(s, "behavior"):
        if not hasattr(s, "lbehavior"):
            print(s.behavior)
        s.lbehavior = s.behavior
    else:
        s.behavior = "none"
