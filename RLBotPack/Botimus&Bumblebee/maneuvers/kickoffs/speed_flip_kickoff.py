from maneuvers.jumps.speed_flip import SpeedFlip
from maneuvers.kickoffs.kickoff import Kickoff
from rlutilities.linear_algebra import norm
from rlutilities.simulation import Car
from tools.game_info import GameInfo
from tools.vector_math import local


class SpeedFlipKickoff(Kickoff):
    """
    Speedflip into the ball. Works only on corner kickoffs. It's useful only against slow kickoffs.
    """
    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car, info)
        self.drive.target_pos = self.info.my_goal.center * 0.05

    def step(self, dt: float):
        car = self.car
        if self.phase == 1:
            if norm(car.velocity) > 1050:
                self.action = SpeedFlip(car, right_handed=local(car, self.info.ball.position)[1] < 0)
                self.phase = 2

        if self.phase == 2:
            if self.action.finished:
                self.finished = True

        super().step(dt)
