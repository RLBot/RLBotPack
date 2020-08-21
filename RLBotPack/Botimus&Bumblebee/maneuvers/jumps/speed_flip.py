from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import norm
from rlutilities.simulation import Car

FIRST_JUMP_DURATION = 0.1
BETWEEN_JUMPS_DELAY = 0.1
SECOND_JUMP_DURATION = 0.05
TIMEOUT = 2.0


class SpeedFlip(Maneuver):
    def __init__(self, car: Car, right_handed=True, use_boost=True):
        super().__init__(car)

        self.direction = 1 if right_handed else -1
        self.use_boost = use_boost
        self.timer = 0.0

    def interruptible(self) -> bool:
        return False

    def step(self, dt: float):

        # Always throttle.
        self.controls.throttle = 1.0

        # Use boost if should after first jump and not supersonic.
        speed = norm(self.car.velocity)
        self.controls.boost = (
            # self.use_boost and self.timer > FIRST_JUMP_DURATION and speed < 2250
            self.use_boost and speed < 2290
        )

        if self.timer < FIRST_JUMP_DURATION:
            self.controls.jump = True
            self.controls.pitch = 1.0

        elif self.timer < FIRST_JUMP_DURATION + BETWEEN_JUMPS_DELAY:
            self.controls.jump = False
            self.controls.pitch = 1.0

        elif (
            self.timer
            < FIRST_JUMP_DURATION + BETWEEN_JUMPS_DELAY + SECOND_JUMP_DURATION
        ):
            self.controls.jump = True
            self.controls.pitch = -1.0
            self.controls.roll = -0.3 * self.direction

        else:
            self.controls.jump = False
            self.controls.pitch = 1.0
            self.controls.roll = -1.0 * self.direction
            self.controls.yaw = -1.0 * self.direction

        self.timer += dt

        self.finished = (self.timer > TIMEOUT) or (
            self.car.on_ground and self.timer > 0.5
        )
