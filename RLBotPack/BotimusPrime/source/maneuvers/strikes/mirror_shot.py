from maneuvers.kit import * 

from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.strike import Strike

class MirrorShot(GroundShot):
    def __init__(self, car: Car, info: GameInfo, target: vec3):
        self.actual_target = target

        mirrors = [self.mirrored_pos(target, 1), self.mirrored_pos(target, -1)]
        mirrors[0][0] *= 1.2
        mirrors[1][0] *= 1.2
        target = Strike.pick_easiest_target(car, info.ball, mirrors)

        super().__init__(car, info, target)

    @staticmethod
    def mirrored_pos(pos: vec3, wall_sign: int):
        return vec3(2 * Arena.size[0] * wall_sign - pos[0], pos[1], pos[2])
