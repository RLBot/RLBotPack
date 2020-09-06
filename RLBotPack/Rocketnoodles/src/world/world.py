from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
from dataclasses import dataclass
from typing import List, Any
from world.components import *
from physics.math import Vec3


@dataclass
class World:
    """Contains information about the state of the world.

    :param packet: Object containing information about the environment.
    :type packet: GameTickPacket
    :param field_info: The field info resulting from rlbots PythonHivemind
    :type field_info: FieldInfoPacket
    """

    def __init__(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        self.cars: List[Car] = [Car(car) for car in packet.game_cars]
        self.teams: List[Team] = [Team(team, self.cars) for team in packet.teams]
        self.ball: Ball = Ball(packet.game_ball)
        self.game: Game = Game(packet.game_info)

        self.boost_pads: List[WorldBoostPad] = []
        for index, (boost_pad_dynamic, boost_pad_static) in enumerate(zip(packet.game_boosts, field_info.boost_pads)):
            self.boost_pads.append(WorldBoostPad(index, boost_pad_dynamic, boost_pad_static))

        self.num_cars: int = packet.num_cars
        self.num_boost: int = packet.num_boost
        self.time_delta: float = 1 / 60

        self.packet: GameTickPacket = packet
        self.field_info: FieldInfoPacket = field_info

    def update_obs(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        """"Update function for the world model. This function is called once every step.

        :param packet: Object containing information about the environment.
        :type packet: GameTickPacket
        :param field_info: The field info resulting from rlbots PythonHivemind
        :type field_info: FieldInfoPacket
        """
        for index, player_info in enumerate(packet.game_cars):
            self.cars[index].update(player_info)
        for index, boost_pad in enumerate(packet.game_boosts):
            self.boost_pads[index].update(boost_pad)

        self.ball.update(packet.game_ball)
        self.game.update(packet.game_info)
        for index, team in enumerate(packet.teams):
            self.teams[index].update(team, self.cars)

        self.packet = packet
        self.field_info = field_info

    def calc_dist_to_ball(self, physics_object):
        return (Vec3.from_other_vec(physics_object.physics.location) - Vec3.from_other_vec(
            self.ball.physics.location)).magnitude()
