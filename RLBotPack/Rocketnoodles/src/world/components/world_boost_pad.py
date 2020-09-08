from world.components import WorldComponent
from dataclasses import dataclass
from rlbot.utils.structures.game_data_struct import Vector3
from rlbot.utils.structures.game_data_struct import BoostPadState, BoostPad


@dataclass
class WorldBoostPad(WorldComponent):
    """BoostPad Component for the world model.

    :param info: Information about the ball.
    :type BoostPadState:
    """

    index: int
    is_active: bool
    timer: float
    location: Vector3

    def __init__(self, index, info: BoostPadState, boostpad: BoostPad):
        self.index = index
        self.update(info)
        self.location = boostpad.location

    def update(self, info: BoostPadState):
        """Update function for the BoostPad class. Updates the internal state of this component to the current step.

        :param info: Information about the boostpads.
        :type info: BoostPadState
        """
        self.is_active = info.is_active
        self.timer = info.timer
