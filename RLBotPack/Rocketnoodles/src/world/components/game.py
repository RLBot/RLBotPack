from world.components import WorldComponent
from dataclasses import dataclass
from rlbot.utils.structures.game_data_struct import GameInfo


@dataclass
class Game(WorldComponent):
    """"Game Component for the world model.

    :param info: Metadata about a single match.
    :type GameInfo:
    """

    game_speed: float
    game_time_remaining: float
    is_kickoff_pause: bool
    is_match_ended: bool
    is_overtime: bool
    is_round_active: bool
    is_unlimited_time: bool
    seconds_elapsed: float
    world_gravity_z: float

    def __init__(self, info: GameInfo):
        self.update(info)

    def update(self, info: GameInfo):
        """Update function for the Game class. Updates the internal state of this component to the current step.

        :param info: Metadata about a single match.
        :type info: GameInfo
        """

        self.game_speed = info.game_speed
        self.game_time_remaining = info.game_time_remaining
        self.is_kickoff_pause = info.is_kickoff_pause
        self.is_match_ended = info.is_match_ended
        self.is_overtime = info.is_overtime
        self.is_round_active = info.is_round_active
        self.is_unlimited_time = info.is_unlimited_time
        self.seconds_elapsed = info.seconds_elapsed
        self.world_gravity_z = info.world_gravity_z
