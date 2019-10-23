from maneuvers.kit import *

from maneuvers.air.recovery import Recovery
from rlutilities.simulation import Field
from rlutilities.mechanics import AerialTurn

class FastRecovery(Maneuver):
    '''Boost down and try to land on all four wheels'''

    def __init__(self, car: Car):
        super().__init__(car)

        self.landing = False
        self.turn = AerialTurn(self.car)
        self.recovery = Recovery(self.car)

    def step(self, dt):
        self.controls.throttle = 1 # in case we're turtling

        if self.landing:
            self.recovery.step(dt)
            self.controls = self.recovery.controls
        else:
            landing_pos = self.find_landing_pos()
            landing_dir = direction(self.car, landing_pos - vec3(0,0,1000))

            self.turn.target = look_at(landing_dir, vec3(0,0,1))
            self.turn.step(dt)
            self.controls = self.turn.controls

            # boost down
            if angle_between(self.car.forward(), landing_dir) < 0.8:
                self.controls.boost = 1
            else:
                self.controls.boost = 0

            # when nearing landing position, start recovery
            if distance(self.car, landing_pos) < clamp(norm(self.car.velocity), 600, 2300):
                self.landing = True

        self.finished = self.car.on_ground

    def find_landing_pos(self, num_points=200, dt=0.0333) -> vec3:
        '''Simulate car falling until it hits a plane and return it's final position'''
        dummy = Car(self.car)
        for i in range(0, num_points):
            dummy.step(Input(), dt)
            dummy.time += dt
            n = Field.collide(sphere(dummy.position, 40)).direction
            if norm(n) > 0.0 and i > 10:
                return dummy.position
        return self.car.position

    def render(self, draw):
        if self.landing:
            self.recovery.render(draw)
                    