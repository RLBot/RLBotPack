from maneuvers.jumps.aim_dodge import AimDodge
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import norm
from utils.intercept import Intercept
from utils.math import clamp
from utils.vector_math import ground_direction


class DodgeStrike(Strike):

    allow_backwards = False
    jump_time_multiplier = 1.0

    def intercept_predicate(self, car, ball):
        return ball.position[2] < 280

    def __init__(self, car, info, target=None):
        self.dodge = AimDodge(car, 0.1, info.ball.position)
        self.dodging = False

        super().__init__(car, info, target)

    def configure(self, intercept: Intercept):
        super().configure(intercept)

        if self.target is None:
            self.arrive.target = intercept.ground_pos + ground_direction(intercept, self.car) * 100
        else:
            self.arrive.target = intercept.ground_pos - ground_direction(intercept, self.target) * 110

        additional_jump = clamp((intercept.ball.position[2]-92) / 500, 0, 1.5) * self.jump_time_multiplier
        self.dodge.jump.duration = 0.05 + additional_jump
        self.dodge.target = intercept.ball.position
        self.arrive.additional_shift = additional_jump * 500

    def interruptible(self) -> bool:
        return not self.dodging and super().interruptible()

    def step(self, dt):
        if self.dodging:
            self.dodge.step(dt)
            self.controls = self.dodge.controls
        else:
            super().step(dt)
            if (
                self.arrive.arrival_time - self.car.time < self.dodge.jump.duration + 0.17
                and abs(self.arrive.drive.target_speed - norm(self.car.velocity)) < 1000
            ):
                self.dodging = True

        if self.dodge.finished:
            self.finished = True
