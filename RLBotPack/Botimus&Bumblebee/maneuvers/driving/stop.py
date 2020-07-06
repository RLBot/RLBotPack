from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import dot


class Stop(Maneuver):

    def step(self, dt):
        vf = dot(self.car.forward(), self.car.velocity)
        if vf > 100:
            self.controls.throttle = -1
        elif vf < -100:
            self.controls.throttle = 1
        else:
            self.controls.throttle = 0
            self.finished = True
