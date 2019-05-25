import Procedure
# import Testing

from Bots import *


def Process(s, game, version=3):
    """Main Loop."""

    Procedure.pre_process(s, game)

    bot_composite(s)
    # bot_default(s)

    Procedure.feedback(s)

    # Testing.graph_path(s)

    return output(s, version)


def output(s, version):
    """Return bot controls"""

    if version == 2:

        U = 32766

        if s.poG:
            s.yaw = s.steer
        else:
            s.powerslide = 0

        if not s.poG and s.roll != 0 and s.counter % 2 == 1 and abs(s.r) > .03 and abs(s.a) < .15:
            s.yaw = s.roll
            s.powerslide = 1

        return [int((s.yaw + 1) * U / 2), int((s.pitch + 1) * U / 2), int(s.throttle * U), int(-s.throttle * U),
                s.jump, s.boost, s.powerslide]

    else:
        return [s.throttle, s.steer, s.pitch, s.yaw, s.roll, s.jump, s.boost, s.powerslide]
