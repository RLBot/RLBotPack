from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from tools.arena import Arena
from tools.game_info import GameInfo


class MirrorStrike(DodgeStrike):
    """
    Strike the ball in a way that it bounces off the wall towards the target.
    This is usually too slow to result in a goal right away, but you can easily follow it up with another shot.
    """
    def __init__(self, car: Car, info: GameInfo, target: vec3):
        self.actual_target = target
        self.info = info

        mirrors = [self.mirrored_pos(target, 1), self.mirrored_pos(target, -1)]
        target = self.pick_easiest_target(car, info.ball, mirrors)

        super().__init__(car, info, target)

    @staticmethod
    def mirrored_pos(pos: vec3, wall_sign: int):
        mirrored_x = 2 * Arena.size[0] * wall_sign - pos[0]
        return vec3(mirrored_x, pos[1], pos[2])
