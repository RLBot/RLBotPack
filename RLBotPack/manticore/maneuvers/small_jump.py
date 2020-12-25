from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from maneuvers.recovery import RecoveryManeuver
from utility.rlmath import sign
from utility.vec import proj_onto_size, angle_between, dot, normalize


class SmallJumpManeuver(Maneuver):
    def __init__(self, bot, target=None, boost=False):
        super().__init__()
        self.target = target
        self.boost = boost
        self.controls = SimpleControllerState()
        self.start_time = bot.info.time
        self.almost_done = False

        self._t_first_unjump = 0.20
        self._t_aim_prepare = 0.35
        self._t_aim = 0.6
        self._t_second_jump = 0.65
        self._t_second_unjump = 0.95
        self._t_finishing = 1.45  # After this, fix orientation until lands on ground

        self._max_speed = 2000  # Don't boost if above this speed
        self._boost_ang_req = 0.25

    def exec(self, bot):
        ct = bot.info.time - self.start_time

        # Target is allowed to be a function that takes bot as a parameter. Check what it is
        if callable(self.target):
            target = self.target(bot)
        else:
            target = self.target

        # Get car and reset controls
        car = bot.info.my_car
        self.controls.throttle = 1
        self.controls.yaw = 0
        self.controls.pitch = 0
        self.controls.jump = False

        # To boost or not to boost, that is the question
        car_to_target = target - car.pos
        vel_p = proj_onto_size(car.vel, car_to_target)
        angle = angle_between(car_to_target, car.forward)
        self.controls.boost = self.boost and angle < self._boost_ang_req and vel_p < self._max_speed

        # States of dodge (note reversed order)
        # Land on ground
        if ct >= self._t_finishing:
            self.almost_done = True
            if car.on_ground:
                self.done = True
            else:
                bot.plan = RecoveryManeuver()
                self.done = True
            return self.controls
        elif ct >= self._t_second_unjump:
            # Stop pressing jump and rotate and wait for flip is done
            pass

        elif ct >= self._t_aim:
            if ct >= self._t_second_jump:
                self.controls.jump = 1

            # Direction, yaw, pitch, roll
            if self.target is None:
                self.controls.roll = 0
                self.controls.pitch = -1
                self.controls.yaw = 0
            else:
                target_local = dot(car_to_target, car.rot)
                target_local.z = 0

                direction = normalize(target_local)

                self.controls.roll = 0
                self.controls.pitch = -direction.x
                self.controls.yaw = sign(car.rot.get(2, 2)) * direction.y

        # Pitch slightly upwards before starting the dodge
        elif ct >= self._t_aim_prepare:
            self.controls.pitch = 1

        # Stop pressing jump
        elif ct >= self._t_first_unjump:
            pass

        # First jump
        else:
            self.controls.jump = 1

        return self.controls
