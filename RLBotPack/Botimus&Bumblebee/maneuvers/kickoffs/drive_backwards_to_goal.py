from maneuvers.driving.drive import Drive
from maneuvers.maneuver import Maneuver
from rlutilities.simulation import Car
from tools.game_info import GameInfo
from tools.vector_math import ground_distance


class DriveBackwardsToGoal(Maneuver):
    """
    Simply drive backwards until we are in the center of our goal.
    This is useful if we are the nearest car to our goal on kickoff, in case we lose a kickoff horribly,
    we are in a good position to save.
    Note: This isn't an actual kickoff maneuver (it doesn't go for the ball), so it doesn't inherit from Kickoff.
    """

    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car)
        self.drive = Drive(car)
        self.drive.backwards = True
        self.drive.target_pos = info.my_goal.center
        self.drive.target_speed = 1300

    def step(self, dt: float):
        self.drive.step(dt)
        self.controls = self.drive.controls

        if ground_distance(self.car, self.drive.target_pos) < 100:
            self.finished = True
