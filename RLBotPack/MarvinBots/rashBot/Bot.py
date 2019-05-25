from Procedure import pre_process, feedback, gather_info
from Handling import controls
from Strategy import strategy
from Util import U
from rlbot.utils.structures.quick_chats import QuickChats


def Process(s, game, version=3):

    pre_process(s, game)
    gather_info(s)
    strategy(s)
    controls(s)
    feedback(s)

    return output(s, version)


def output(s, version):
    if version == 2:

        # if s.roll != 0 :
        #   s.yaw = s.roll
        #   s.powerslide = 1

        if s.poG:
            s.yaw = s.steer

        return [int((s.yaw + 1) * U / 2), int((s.pitch + 1) * U / 2),
                int(s.throttle * U), int(-s.throttle * U),
                s.jump, s.boost, s.powerslide]

    else:

        return [s.throttle, s.steer, s.pitch, s.yaw, s.roll,
                s.jump, s.boost, s.powerslide]
