from rlbot.utils.structures.game_data_struct import PlayerInfo
from rlbot.utils.structures.game_data_struct import Physics
from rlbot.utils.structures.game_data_struct import BoxShape
from world.components import WorldComponent
from dataclasses import dataclass


@dataclass
class Car(WorldComponent):
    """"Car Component for the world model.

    :param info: Information about a single car.
    :type PlayerInfo:
    """

    spawn_id: int
    physics: Physics
    is_demolished: bool
    has_wheel_contact: bool
    is_super_sonic: bool
    is_bot: bool
    jumped: bool
    double_jumped: bool
    name: str
    team: int
    boost: int
    hitbox: BoxShape

    def __init__(self, info: PlayerInfo):
        self.update(info)

    def update(self, info: PlayerInfo):
        """Update function for the Car class. Updates the internal state of this component to the current step.

        :param info: Information about a single car.
        :type info: PlayerInfo
        """

        self.spawn_id: int = info.spawn_id
        self.physics: Physics = info.physics
        self.is_demolished: bool = info.is_demolished
        self.has_wheel_contact: bool = info.has_wheel_contact
        self.is_super_sonic: bool = info.is_super_sonic
        self.is_bot: bool = info.is_bot
        self.jumped: bool = info.jumped
        self.double_jumped: bool = info.double_jumped
        self.name: str = info.name
        self.team: int = info.team
        self.boost: int = info.boost
        self.hitbox: BoxShape = info.hitbox
