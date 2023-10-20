from maneuvers.driving.drive import Drive
from maneuvers.jumps.half_flip import HalfFlip
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import norm, vec3
from rlutilities.simulation import Car, BoostPad


class HalfFlipPickup(Maneuver):
    """
    Drive backwards towards a boost pad, halfflip, pick up the boost pad and then turn towards the center.
    This is useful on kickoffs when there are two cars on the corner position.
    Note: This isn't an actual kickoff maneuver (it doesn't go for the ball), so it doesn't inherit from Kickoff.
    """
    def __init__(self, car: Car, pad: BoostPad):
        super().__init__(car)
        self.drive = Drive(car, target_pos=pad.position, target_speed=2300, backwards=True)
        self.phase = 1
        self.action = self.drive

    def interruptible(self) -> bool:
        return self.action is self.drive

    def step(self, dt: float):
        if self.phase == 1 and norm(self.car.velocity) > 600:
            self.action = HalfFlip(self.car)
            self.phase = 2

        if self.phase == 2 and self.action.finished:
            self.drive.target_pos = vec3(0, self.car.position[1], 0)
            self.drive.backwards = False
            self.action = self.drive
            self.phase = 3

        if self.phase == 3 and norm(self.car.velocity) > 1300:
            self.finished = True

        self.action.step(dt)
        self.controls = self.action.controls
