from maneuvers.strikes.clears import DodgeClear, AerialClear, DoubleJumpClear, FastAerialClear
from maneuvers.strikes.strike import Strike
from rlutilities.simulation import Car
from tools.game_info import GameInfo


def any_clear(info: GameInfo, car: Car) -> Strike:
    clears = [
        DodgeClear(car, info),
        # DoubleJumpClear(car, info)
    ]

    if car.boost > 40:  # TODO
        # clears.append(AerialClear(car, info))
        clears.append(FastAerialClear(car, info))

    return min(clears, key=lambda clear: clear.intercept.time)
