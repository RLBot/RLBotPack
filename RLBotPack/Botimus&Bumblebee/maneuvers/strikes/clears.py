from maneuvers.strikes.aerial_strike import AerialStrike, FastAerialStrike
from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.double_jump_strike import DoubleJumpStrike
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3
from tools.arena import Arena
from tools.intercept import Intercept

# make a bunch of points on the side of the arena
_one_side = [vec3(Arena.size[0], Arena.size[1] * i/5, 0) for i in range(-5, 5)]
_other_side = [vec3(-p[0], p[1], 0) for p in _one_side]
_side_points = _one_side + _other_side

# the clears simply pick the easiest point to aim at
# this is not a very elegant solution, so I'll just put a TODO: make this better


class DodgeClear(DodgeStrike):
    def configure(self, intercept: Intercept):
        self.target = self.pick_easiest_target(self.car, intercept.ball, _side_points)
        super().configure(intercept)


class AerialClear(AerialStrike):
    def configure(self, intercept: Intercept):
        self.target = self.pick_easiest_target(self.car, intercept.ball, _side_points)
        super().configure(intercept)


class FastAerialClear(FastAerialStrike):
    def configure(self, intercept: Intercept):
        self.target = self.pick_easiest_target(self.car, intercept.ball, _side_points)
        super().configure(intercept)


class DoubleJumpClear(DoubleJumpStrike):
    def configure(self, intercept: Intercept):
        self.target = self.pick_easiest_target(self.car, intercept.ball, _side_points)
        super().configure(intercept)
