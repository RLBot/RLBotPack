from maneuvers.driving.drive import Drive
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3, dot, normalize, look_at
from rlutilities.mechanics import Reorient
from rlutilities.simulation import Car, Input
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import ground_distance, ground, ground_direction, direction

MIN_ALIGNMENT = 0.9
MIN_DIST_BEFORE_SPEED_CONTROL = 1500
JUMP_FALSE_TICKS = 2
ALLOWED_TIME_ERROR = 0.1


class DoubleJumpStrike(Strike):

    def intercept_predicate(self, car, ball):
        return 250 < ball.position[2] < 550

    def __init__(self, car: Car, info: GameInfo, target=None):
        self.drive = Drive(car)
        self.reorient = Reorient(car)

        self.jumping = False
        self.time_for_jump = float("inf")
        self.timer = 0.0

        super().__init__(car, info, target)

    def configure(self, intercept: Intercept):
        super().configure(intercept)
        self.drive.target_pos = ground(intercept.position)
        self.time_for_jump = self.double_jump_time_needed(intercept.position[2])
    
    def interruptible(self) -> bool:
        return not self.jumping and super().interruptible()

    def step(self, dt):
        if self.jumping:
            self.controls = Input()
            # first jump for full 0.2 sec
            if self.timer <= 0.2:
                self.controls.jump = True
            # single tick between jumps
            elif self.timer <= 0.2 + dt * JUMP_FALSE_TICKS:
                self.controls.jump = False
            # second jump
            else:
                self.controls.jump = True
                self.jumping = False
            self.timer += dt

        else:
            self.finished = self.intercept.time < self.info.time

            if self.car.on_ground:
                # manage speed before jump
                distance_to_target = ground_distance(self.car.position, self.intercept.position)
                if distance_to_target < MIN_DIST_BEFORE_SPEED_CONTROL:
                    target_speed = distance_to_target / self.time_for_jump
                    self.drive.target_speed = -target_speed if self._should_strike_backwards else target_speed
                    self.drive.step(dt)
                    self.controls = self.drive.controls

                else:
                    super().step(dt)
            
                # decide when to jump
                ground_vel = ground(self.car.velocity)
                direction_to_target = ground_direction(self.car.position, self.intercept.position)
                alignment = dot(normalize(ground_vel), direction_to_target)
                # check alignment
                if alignment >= MIN_ALIGNMENT:
                    # check that speed is correct
                    speed_in_direction = dot(ground_vel, direction_to_target)
                    time_to_target = distance_to_target / speed_in_direction
                    if self.time_for_jump - ALLOWED_TIME_ERROR <= time_to_target <= self.time_for_jump + ALLOWED_TIME_ERROR:
                        self.jumping = True

            # after jump (when the car is in the air)
            else:
                # face the ball for some additional height
                self.reorient.target_orientation = look_at(direction(self.car.position, self.info.ball), vec3(0, 0, 1))
                self.reorient.step(dt)
                self.controls = self.reorient.controls

    @staticmethod
    def double_jump_time_needed(height):
        """Return the time needed for the double jump to reach a given height"""
        # polynomial approximation
        a = 1.872348977E-8 * height * height * height
        b = -1.126747937E-5 * height * height
        c = 3.560647225E-3 * height
        d = -7.446058499E-3
        return a + b + c + d
