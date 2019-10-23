from maneuvers.kit import *

from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.strike import Strike

class CornerShot(GroundShot):
    def __init__(self, car: Car, info: GameInfo, target_goal: vec3):
        self.actual_target = target_goal

        corners = [target_goal - vec3(Arena.size[0], 0, 0), target_goal + vec3(Arena.size[0], 0, 0)]
        target = Strike.pick_easiest_target(car, info.ball, corners)

        super().__init__(car, info, target)
        