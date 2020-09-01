from maneuvers.kickoffs.kickoff import Kickoff
from maneuvers.kickoffs.simple_kickoff import SimpleKickoff
from maneuvers.kickoffs.speed_flip_dodge_kickoff import SpeedFlipDodgeKickoff
from rlutilities.simulation import Car
from tools.game_info import GameInfo


def choose_kickoff(info: GameInfo, car: Car) -> Kickoff:
    if abs(car.position[0]) > 1000:
        return SpeedFlipDodgeKickoff(car, info)
    else:
        return SimpleKickoff(car, info)
