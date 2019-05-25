import Handling
import Strategy
import Shooter.Strategy
import Shooter.Handling
import Fastbot.Strategy
import Fastbot.Handling
from Generic.SimpleBot import *
from util import a3, dist3d


def bot_default(s):
    Strategy.plan(s)
    Handling.controls(s)
    s.behavior = 'Default'


def bot_shooter(s):
    Shooter.Strategy.plan(s)
    Shooter.Handling.controls(s)
    s.behavior = 'Shooter'


def bot_fastbot(s):
    Fastbot.Strategy.plan(s)
    Fastbot.Handling.controls(s)
    s.behavior = 'Fastbot'


def go_to(s, location):
    GoTo(s, location)
    s.behavior = 'go_to'


def bot_composite(s):

    GeneralInfo(s)

    safe_haven = set_dist(s.bL, s.ogoal, min(dist3d(s.bL, s.ogoal) - 200, dist3d(s.pV) + 1200, 2000))
    safe_haven[2] = 0

    # obehind = dist3d(s.oL, s.ogoal) < dist3d(s.bL, s.ogoal)
    behind = dist3d(s.pL, s.ogoal) > dist3d(s.bL, s.ogoal)
    infront = s.bL[1] * s.color > s.pL[1] * s.color + 99

    # blockable = min(abs(s.oglinex), abs(s.obglinex)) < 999 and s.bV[1] * s.color < 0 and infront

    if s.kickoff:
        bot_default(s)
    else:
        if s.bL[2] > 500 and s.pL[2] > 60 and dist3d(s.bL, s.goal) < 4500 and s.poG and not infront:
            go_to(s, (safe_haven + s.bL) * a3([1, 1, 0]))
        elif dist3d(s.ogoal, s.bL) < 3000 or (s.bV[1] * s.color < 0 and s.pV[1] * s.color < 0 and s.bd < 999):
                bot_fastbot(s)
        else:
            if not behind and dist3d(s.oL, s.bL) > 2000:
                bot_shooter(s)
            else:
                bot_default(s)

    # if hasattr(s, "lbehavior"):
    #     if s.lbehavior != s.behavior:
    #         print(s.behavior)
