from world.components import WorldComponent
from dataclasses import dataclass
from rlbot.utils.structures.game_data_struct import BallInfo
from rlbot.utils.structures.game_data_struct import DropShotInfo
from rlbot.utils.structures.game_data_struct import CollisionShape
from rlbot.utils.structures.game_data_struct import Touch
from rlbot.utils.structures.game_data_struct import Physics


@dataclass
class Ball(WorldComponent):
    """"Ball Component for the world model.

    :param info: Information about the ball.
    :type BallInfo:
    """

    collision_shape: CollisionShape
    drop_shot_info: DropShotInfo
    latest_touch: Touch
    physics: Physics

    def __init__(self, info: BallInfo):
        self.update(info)

    def update(self, info: BallInfo):
        """"Update function for the ball class. Updates the internal state of this component to the current step.

        :param info: Information about the ball.
        :type info: BallInfo
        """
        self.collision_shape = info.collision_shape
        self.drop_shot_info = info.drop_shot_info
        self.latest_touch = info.latest_touch
        self.physics = info.physics
