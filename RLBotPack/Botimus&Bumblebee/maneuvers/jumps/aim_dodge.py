from maneuvers.jumps.air_dodge import AirDodge
from rlutilities.linear_algebra import vec3, normalize, look_at
from rlutilities.mechanics import Reorient
from rlutilities.simulation import Car
from tools.vector_math import direction


class AimDodge(AirDodge):
    """
    Execute a regular dodge, but also turn the car towards the target (and slightly more up) before dodging.
    Useful for dodging into the ball.
    """

    def __init__(self, car: Car, duration: float, target: vec3):
        super().__init__(car, duration, target)
        self.reorient = Reorient(car)

    def step(self, dt):
        super().step(dt)

        if not self.jump.finished and not self.car.on_ground:
            target_direction = direction(self.car, self.target + vec3(0, 0, 200))
            up = target_direction * (-1)
            up[2] = 1
            up = normalize(up)
            self.reorient.target_orientation = look_at(target_direction, up)
            self.reorient.step(dt)
            self.controls.pitch = self.reorient.controls.pitch
            self.controls.yaw = self.reorient.controls.yaw
            self.controls.roll = self.reorient.controls.roll
