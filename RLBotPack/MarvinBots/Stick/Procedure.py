from util import *


def pre_process(s, packet):

    data_format(s, packet)

    if not hasattr(s, "counter"):
        init(s)

    prepare(s)


def data_format(s, packet):

    # player
    player = packet.game_cars[s.index]

    s.pL = a3v(player.physics.location)
    s.pR = a3r(player.physics.rotation)
    s.pV = a3v(player.physics.velocity)
    s.paV = a3v(player.physics.angular_velocity)
    s.pJ = player.jumped
    s.pdJ = player.double_jumped
    s.poG = player.has_wheel_contact
    s.pB = player.boost
    s.pS = player.is_super_sonic
    s.color = -sign(player.team)
    s.team = player.team

    # ball
    ball = packet.game_ball

    s.bL = a3v(ball.physics.location)
    s.bV = a3v(ball.physics.velocity)
    s.baV = a3v(ball.physics.angular_velocity)

    # opponent
    oppIndex = not s.index

    if packet.num_cars > 2:  # use closest opponent to the ball
        oppIndex = -1
        for i in range(packet.num_cars):
            if packet.game_cars[i].team != player.team:
                if oppIndex == -1 or (dist3d(a3v(packet.game_cars[i].physics.location), s.bL) <
                                      dist3d(a3v(packet.game_cars[oppIndex].physics.location), s.bL)):
                    oppIndex = i

    if oppIndex < packet.num_cars:
        opp = packet.game_cars[oppIndex]
        s.oL = a3v(opp.physics.location)
        s.oR = a3r(opp.physics.rotation)
        s.oV = a3v(opp.physics.velocity)
        s.oB = opp.boost
    else:
        s.oV = s.oR = np.zeros(3)
        s.oL = s.oV + 6e3
        s.oB = 0

    # game info
    info = packet.game_info

    s.time = info.seconds_elapsed
    s.active = packet.game_info.is_round_active
    s.bH = not info.is_kickoff_pause
    s.G = info.world_gravity_z

    field_info = s.get_field_info()

    if not hasattr(s, 'large_pads') and field_info.num_boosts > 1:

        for i in range(field_info.num_goals):
            if field_info.goals[i].team_num != s.team:
                s.goal = a3v(field_info.goals[i].location)
                s.goald = -a3v(field_info.goals[i].direction)
            else:
                s.ogoal = a3v(field_info.goals[i].location)
                s.ogoald = -a3v(field_info.goals[i].direction)
            if hasattr(s, 'goal') and hasattr(s, 'ogoal'):
                break

        s.large_pads = []
        s.small_pads = []

        for i in range(field_info.num_boosts):
            pad = field_info.boost_pads[i]
            pad_type = s.large_pads if pad.is_full_boost else s.small_pads
            padobj = BoostPad(i, a3v(pad.location))
            pad_type.append(padobj)

    if hasattr(s, 'large_pads'):
        for pad_type in (s.large_pads, s.small_pads):
            for pad in pad_type:
                pad.is_active = packet.game_boosts[pad.index].is_active
                pad.timer = packet.game_boosts[pad.index].timer

    # if abs(s.G) > 1 or not hasattr(s, 'counter'):
    #     zero_g(s)


def init(s):
    """initializing some variables"""

    s.counter = -1

    s.throttle = s.steer = s.pitch = s.yaw = s.roll = s.jump = s.boost = 0
    s.handbrake = s.ljump = 0

    s.aT = s.gT = s.sjT = s.djT = s.time

    s.dodge = s.jumper = 0

    s.goal = a3l([0, 5120 * s.color, 0])
    s.goald = a3l([0, 1 * s.color, 0])

    s.ogoal = -s.goal
    s.ogoald = -s.goald

    feedback(s)


def prepare(s):

    s.bx, s.by, s.bz = local(s.bL, s.pL, s.pR)
    s.bd, s.ba, s.bi = spherical(s.bx, s.by, s.bz)
    s.iv, s.rv, s.av = local(s.paV, 0, s.pR)
    s.pxv, s.pyv, s.pzv = local(s.pV, 0, s.pR)
    s.pvd, s.pva, s.pvi = spherical(s.pxv, s.pyv, s.pzv)
    s.bxv, s.byv, s.bzv = local(s.bV, 0, s.pR)
    s.bvd, s.bva, s.bvi = spherical(s.bxv, s.byv, s.bzv)

    s.obd = dist3d(s.bL, s.oL)

    if s.poG and not s.lpoG:
        s.gT = s.time
    if s.lpoG and not s.poG:
        s.aT = s.time

    s.airtime = s.time - s.aT
    s.gtime = s.time - s.gT
    s.djtime = s.time - s.djT

    if s.lljump and not s.ljump:
        s.sjT = s.ltime

    s.sjtime = s.time - s.sjT

    if s.poG and s.lpoG:
        s.airtime = s.sjtime = s.djtime = 0
    else:
        s.gtime = 0

    if s.poG:
        s.jcount = 2
    elif s.pdJ or (s.sjtime > 1.25 and s.pJ):
        s.jcount = 0
    else:
        s.jcount = 1

    if s.jcount == 0 and s.airtime > .25 or (s.poG and not s.lpoG):
        s.dodge = s.jumper = 0

    s.dtime = s.time - s.ltime
    if s.dtime != 0:
        s.fps = 1 / s.dtime
    else:
        s.fps = 0


def feedback(s):

    s.ltime = s.time
    s.lpoG = s.poG

    s.lljump = s.ljump

    s.lthrottle, s.lsteer = s.throttle, s.steer
    s.lpitch, s.lyaw, s.lroll = s.pitch, s.yaw, s.roll
    s.ljump, s.lboost, s.lhandbrake = s.jump, s.boost, s.handbrake

    s.counter += 1


class BoostPad:

    def __init__(self, index, pos, is_active=True, timer=0.0):
        self.index = index
        self.pos = pos
        self.is_active = is_active
        self.timer = timer


def zero_g(s):
    from rlbot.utils.game_state_util import GameState, GameInfoState

    game_info_state = GameInfoState(world_gravity_z=-0.1, game_speed=1.5)
    game_state = GameState(game_info=game_info_state)
    s.set_game_state(game_state)
