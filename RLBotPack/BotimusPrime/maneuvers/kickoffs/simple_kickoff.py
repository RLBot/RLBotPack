from maneuvers.jumps.air_dodge import AirDodge
from maneuvers.kickoffs.kickoff import Kickoff
from rlutilities.linear_algebra import vec3, norm, sgn
from rlutilities.simulation import Car
from utils.game_info import GameInfo
from utils.vector_math import distance


class SimpleKickoff(Kickoff):
    """
    Go straight for the ball, dodge in the middle and at the end
    """
    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car, info)
        self.drive.target_pos = vec3(0, sgn(info.my_goal.center[1]) * 100, 0)

    def interruptible(self) -> bool:
        return self.action is self.drive

    def step(self, dt):
        car = self.car

        if self.phase == 1:
            if norm(car.velocity) > 1400:
                self.phase = 2
                self.action = AirDodge(car, 0.05, car.position + car.velocity)

        if self.phase == 2:
            self.action.controls.boost = self.action.state_timer < 0.1

            if car.on_ground and self.action.finished:
                self.action = self.drive
                self.phase = 3

        if self.phase == 3:
            if distance(car, vec3(0, 0, 93)) < norm(car.velocity) * 0.4:
                self.phase = 4
                self.action = AirDodge(car, 0.05, self.info.ball.position)

                self.counter_fake_kickoff()
        
        if self.phase == 4:
            if self.action.finished:
                self.finished = True

        super().step(dt)
