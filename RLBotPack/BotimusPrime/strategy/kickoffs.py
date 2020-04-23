from maneuvers.kickoffs.kickoff import Kickoff
from maneuvers.kickoffs.simple_kickoff import SimpleKickoff
from maneuvers.kickoffs.speed_flip_kickoff import SpeedFlipKickoff
from rlutilities.simulation import Car
from utils.game_info import GameInfo


class KickoffStrategy:
    @staticmethod
    def choose_kickoff(info: GameInfo, car: Car) -> Kickoff:
        if abs(car.position[0]) > 1000:
            return SpeedFlipKickoff(car, info)
        else:
            return SimpleKickoff(car, info)
