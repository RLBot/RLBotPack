from maneuvers.kit import *


class Stop(Maneuver):

    def step(self, dt):
        vf = dot(self.car.forward(), self.car.vel)
        if vf > 100:
            self.controls.throttle = -1
        elif vf < -100:
            self.controls.throttle = 1
        else:
            self.controls.throttle = 0
            self.finished = True
