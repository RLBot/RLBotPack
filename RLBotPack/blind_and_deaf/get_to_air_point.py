from rlutilities.mechanics import Drive
from rlutilities.simulation import Car, Input, Game, GameState
from rlutilities.linear_algebra import vec3, normalize, look_at, norm, xy, angle_between
from hover import Hover


class GetToAirPoint:
    """Drive towards the point, jump and start hovering when near enough."""

    def __init__(self, car: Car, info: Game):
        self.target: vec3 = None
        self.car: Car = car
        self.info = info

        self.hover = Hover(car)
        self.drive = Drive(car)
        
        self.controls: Input = Input()

        self.__time_spent_on_ground = 0.0

    def step(self, dt):
        if self.car.on_ground and norm(self.car.position + self.car.velocity - xy(self.target)) > 2500:
            self.drive.speed = 1000
            self.drive.target = self.target
            self.drive.step(dt)
            self.controls = self.drive.controls
            self.controls.handbrake = angle_between(self.car.forward(), self.target - self.car.position) > 1.2
            return

        self.hover.target = self.target
        self.hover.up = normalize(self.car.position * -1)
        self.hover.step(dt)
        self.controls = self.hover.controls

        self.controls.throttle = not self.car.on_ground
        self.controls.jump = (self.car.position[2] < 30 or self.car.on_ground) and self.__time_spent_on_ground > 0.1

        if self.info.state == GameState.Active:
            self.__time_spent_on_ground += dt
        if not self.car.on_ground:
            self.__time_spent_on_ground = 0.0
