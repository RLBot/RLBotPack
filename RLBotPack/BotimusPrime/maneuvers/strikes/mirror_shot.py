from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from utils.arena import Arena
from utils.game_info import GameInfo


class MirrorShot(DodgeShot):
    def __init__(self, car: Car, info: GameInfo, target: vec3):
        self.actual_target = target

        mirrors = [self.mirrored_pos(target, 1), self.mirrored_pos(target, -1)]
        target = Strike.pick_easiest_target(car, info.ball, mirrors)

        super().__init__(car, info, target)

    @staticmethod
    def mirrored_pos(pos: vec3, wall_sign: int):
        return vec3(2 * Arena.size[0] * wall_sign - pos[0], pos[1], pos[2])
