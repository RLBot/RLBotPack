from typing import Optional, Set

from rlutilities.simulation import Car, BoostPad, BoostPadState
from tools.game_info import GameInfo
from tools.intercept import estimate_time
from tools.vector_math import distance


def choose_boostpad_to_pickup(info: GameInfo, car: Car, forbidden_pads: Set[BoostPad] = None) -> Optional[BoostPad]:
    if forbidden_pads is None:
        forbidden_pads = set()

    # consider pads which are available or going to spawn before we can reach them
    active_pads = {pad for pad in info.large_boost_pads if pad.state == BoostPadState.Available}
    soon_active_pads = {pad for pad in info.large_boost_pads if estimate_time(car, pad.position) * 0.7 > pad.timer}

    valid_pads = active_pads | soon_active_pads - forbidden_pads
    if not valid_pads:
        return None

    # a good candidate should be somewhere between us, our goal, and the ball
    # the easiest way to do that is to just take a weighted average of those positions
    pos = (info.ball.position + car.position * 2 + info.my_goal.center * 2) / 5

    # and pick the closest valid pad to that position
    return min(valid_pads, key=lambda pad: distance(pad.position, pos))
