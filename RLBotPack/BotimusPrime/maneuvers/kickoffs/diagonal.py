from maneuvers.kit import *

from maneuvers.driving.drive import Drive
from rlutilities.mechanics import Dodge

class DiagonalKickoff(Maneuver):
    '''Dodge forward once to get there faster.'''
    def __init__(self, car: Car, info: GameInfo):
        super().__init__(car)
        self.info = info

        self.drive = Drive(car)
        self.drive.target_speed = 2300

        self.dodge = Dodge(car)
        self.dodge.duration = 0.1
        self.dodge.direction = normalize(info.their_goal)

        self.phase = 0

    def step(self, dt):
        if self.phase == 0:
            self.controls.throttle = 1
            self.controls.boost = 1
            if ground_distance(self.car, self.info.ball) < 2950:
                print("entering phase 1")
                self.phase = 1
        
        if self.phase == 1:
            self.dodge.step(dt)
            self.controls = self.dodge.controls
            if self.dodge.finished and self.car.on_ground:
                print("entering phase 2")
                self.phase = 2
                self.dodge = Dodge(self.car)
                self.dodge.duration = 0.18
                self.dodge.direction = direction(self.car.position, self.info.ball.position)
        
        if self.phase == 2:
            self.drive.step(dt)
            self.controls = self.drive.controls
            if distance(self.car, self.info.ball) < 850:
                print("entering phase 3")
                self.phase = 3
                

        if self.phase == 3:
            self.dodge.step(dt)
            self.controls = self.dodge.controls

        self.finished = self.info.ball.position[0] != 0 and self.dodge.finished

    def render(self, draw: DrawingTool):
        pass
