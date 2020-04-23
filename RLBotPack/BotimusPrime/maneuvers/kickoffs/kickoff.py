from maneuvers.driving.drive import Drive
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from utils.drawing import DrawingTool
from utils.game_info import GameInfo
from utils.vector_math import distance


class Kickoff(Maneuver):
    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car)
        self.info: GameInfo = info

        self.drive = Drive(car, target_speed=2300)

        self.action: Maneuver = self.drive
        self.phase = 1

    def interruptible(self) -> bool:
        return False

    def counter_fake_kickoff(self):
        if any(distance(self.info.ball, opponent) < 1500 for opponent in self.info.get_opponents(self.car)):
            return

        self.phase = "anti-fake-kickoff"
        self.action = self.drive

    def step(self, dt: float):
        if self.phase == "anti-fake-kickoff":
            self.drive.target_pos = vec3(80, 0, 0)
            self.finished = self.info.ball.position[1] != 0

        self.action.step(dt)
        self.controls = self.action.controls

    def render(self, draw: DrawingTool):
        if hasattr(self.action, "render"):
            self.action.render(draw)
