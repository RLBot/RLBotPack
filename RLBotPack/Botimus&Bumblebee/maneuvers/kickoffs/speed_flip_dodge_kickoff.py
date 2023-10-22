from maneuvers.jumps.air_dodge import AirDodge
from maneuvers.jumps.speed_flip import SpeedFlip
from maneuvers.kickoffs.kickoff import Kickoff
from rlutilities.linear_algebra import norm, vec3
from rlutilities.simulation import Car
from tools.game_info import GameInfo
from tools.vector_math import local, ground_distance


class SpeedFlipDodgeKickoff(Kickoff):
    """
    Speed flip and then dodge into the ball. Works only on corner kickoffs.
    """

    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car, info)
        self.drive.target_pos = self.info.my_goal.center * 0.05
        self._speed_flip_start_time = 0.0

    def step(self, dt: float):
        car = self.car
        if self.phase == 1:
            if norm(car.velocity) > 800:
                self.action = SpeedFlip(car, right_handed=local(car, self.info.ball.position)[1] < 0)
                self.phase = 2
                self._speed_flip_start_time = car.time

        if self.phase == 2:
            if self.action.finished and self.car.on_ground:
                self.action = self.drive
                self.drive.target_pos = vec3(0, 0, 0)
                self.phase = 3

        if self.phase == 3:
            if ground_distance(self.car, vec3(0, 0, 0)) < 500:
                self.action = AirDodge(car, 0.1, vec3(0, 0, 0))
                self.phase = 4
                self.counter_fake_kickoff()

        if self.phase == 4:
            if self.action.finished:
                self.finished = True

        # abort when taking too long
        if car.time > self._speed_flip_start_time + 3.0: self.finished = True

        super().step(dt)
