from typing import Optional

from rlbot.utils.structures.bot_input_struct import PlayerInput

from maneuvers.maneuver import Maneuver
from rlutilities.simulation import Input, Car


class Drone:
    def __init__(self, car: Car, index: int):
        self.car = car
        self.index = index
        self.controls: Input = Input()
        self.maneuver: Optional[Maneuver] = None

    def get_player_input(self) -> PlayerInput:
        player_input = PlayerInput()
        player_input.throttle = self.controls.throttle
        player_input.steer = self.controls.steer
        player_input.pitch = self.controls.pitch
        player_input.yaw = self.controls.yaw
        player_input.roll = self.controls.roll
        player_input.jump = self.controls.jump
        player_input.boost = self.controls.boost
        player_input.handbrake = self.controls.handbrake
        return player_input
