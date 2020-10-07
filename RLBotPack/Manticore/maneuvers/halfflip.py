from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from maneuvers.recovery import RecoveryManeuver
from utility.vec import proj_onto_size


class HalfFlipManeuver(Maneuver):
    def __init__(self, bot, boost=False):
        super().__init__()

        self.boost = boost
        self.maneuver_start_time = bot.info.time
        self.halfflip_start_time = bot.info.time
        self._almost_finished = False

        self._t_first_jump_end = 0.1
        self._t_second_jump_begin = self._t_first_jump_end + 0.08
        self._t_second_jump_end = self._t_second_jump_begin + 0.25
        self._t_roll_begin = self._t_second_jump_begin + 0.35
        self._t_finishing = self._t_second_jump_begin + 0.82  # After this, fix orientation until lands on ground

        self._max_speed = 2100  # Don't boost if above this speed

    def exec(self, bot) -> SimpleControllerState:
        man_ct = bot.info.time - self.maneuver_start_time
        controls = SimpleControllerState()

        car = bot.info.my_car
        vel_f = proj_onto_size(car.vel, car.forward)

        # Reverse a bit
        if vel_f > -50 and man_ct < 0.3:
            controls.throttle = -1
            self.halfflip_start_time = bot.info.time
            return controls

        ct = bot.info.time - self.halfflip_start_time

        # States of jump
        if ct >= self._t_finishing:
            self._almost_finished = True
            controls.throttle = 1
            controls.boost = self.boost
            if car.on_ground:
                self.done = True
            else:
                bot.maneuver = RecoveryManeuver()
                self.done = True
        elif ct >= self._t_roll_begin:
            controls.pitch = -1
            controls.roll = 1
        elif ct >= self._t_second_jump_end:
            controls.pitch = -1
        elif ct >= self._t_second_jump_begin:
            controls.jump = 1
            controls.pitch = 1
        elif ct >= self._t_first_jump_end:
            controls.pitch = 1
        else:
            controls.jump = 1
            controls.throttle = -1
            controls.pitch = 1

        return controls
