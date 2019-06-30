from maneuvers.kit import *

from maneuvers.strikes.strike import Strike
from maneuvers.jumps.aim_dodge import AimDodge

class DodgeStrike(Strike):

    allow_backwards = True

    def intercept_predicate(self, car, ball):
        return ball.pos[2] < 280

    def __init__(self, car, info, target=None):
        self.dodge = AimDodge(car, 0.1, info.ball.pos)
        self.dodging = False

        super().__init__(car, info, target)

    def configure(self, intercept: Intercept):
        super().configure(intercept)

        if self.target is None:
            self.arrive.target = intercept.ground_pos + ground_direction(intercept, self.car) * 100
        else:
            self.arrive.target = intercept.ground_pos - ground_direction(intercept.ground_pos, self.target) * 110

        self.dodge.jump.duration =  0.05 + clamp((intercept.ball.pos[2]-92) / 600, 0, 1.5)
        self.dodge.target = intercept.ball.pos


    def step(self, dt):
        if self.dodging:
            self.dodge.step(dt)
            self.controls = self.dodge.controls
        else:
            super().step(dt)
            if self.arrive.time - self.car.time < self.dodge.jump.duration + 0.2:
                self.dodging = True
        self.finished = self.finished or self.dodge.finished
