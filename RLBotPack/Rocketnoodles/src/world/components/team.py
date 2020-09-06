from world.components import WorldComponent
from rlbot.utils.structures.game_data_struct import TeamInfo
from typing import List
from world.components import Car


class Team(WorldComponent):
    """"Team Component for the world model.

        :param info: Metadata about a single team.
        :type TeamInfo:
        """

    index: int
    score: int
    cars: List[Car]

    def __init__(self, info: TeamInfo, cars: List[Car]):
        self.index = info.team_index
        self.update(info, cars)

    def update(self, info: TeamInfo, cars: List[Car]):
        """Updates the internal state of this component to the current step.

        :param info: Metadata about a single team.
        :type info: TeamInfo
        :param cars: All car components of the existing cars in the game
        :type cars: List[Car]
        """
        self.score = info.score
        self.cars = [car for car in cars if car.team == self.index]
