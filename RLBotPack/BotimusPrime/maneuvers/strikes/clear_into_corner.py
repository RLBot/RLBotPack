from maneuvers.strikes.dodge_shot import DodgeShot
from rlutilities.linear_algebra import vec3
from utils.arena import Arena
from utils.intercept import Intercept


class ClearIntoCorner(DodgeShot):

    def __init__(self, car, info):
        super().__init__(car, info)

    def configure(self, intercept: Intercept):
        one_side = [vec3(Arena.size[0], Arena.size[1] * i/5, 0) for i in range(-5, 5)]
        other_side = [vec3(-p[0], p[1], 0) for p in one_side]

        self.target = self.pick_easiest_target(self.car, intercept.ball, one_side + other_side)
        super().configure(intercept)