from maneuvers.kit import *


class AirHover(Maneuver):
    P = 1.8
    D = 2.5

    def __init__(self, car: Car, target: vec3):
        super().__init__(car)
        self.turn = AerialTurn(car)
        self.target = target
        self.jump = AirDodge(car, 0.2)

    def step(self, dt):
        if not self.jump.finished:
            self.jump.step(dt)
            self.controls = self.jump.controls
            return
        
        delta_target = self.target - self.car.pos
        target_direction = normalize(vec3(
            (delta_target[0]) * self.P - self.car.vel[0] * self.D,
            (delta_target[1]) * self.P - self.car.vel[1] * self.D,
            1000
        ))

        self.turn.target = look_at(target_direction, self.car.up())    

        self.turn.step(dt)
        self.controls = self.turn.controls
        self.controls.boost = 0

        if (delta_target[2] - self.car.vel[2] * 0.5) > 0:
            self.controls.boost = 1

        if dot(self.car.forward(), vec3(0, 0, 1)) < 0.5:
            self.controls.boost = 1


        
