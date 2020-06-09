from random import random
from threading import Thread
from time import sleep
from typing import List

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import CarState, GameState, Physics, Vector3
from rlbot.utils.structures.game_data_struct import PlayerInfo, Rotator
from rlbot_action_server.bot_action_broker import BotActionBroker, run_action_server, find_usable_port
from rlbot_action_server.bot_holder import set_bot_action_broker
from rlbot_action_server.formatting_utils import highlight_player_name
from rlbot_action_server.models import BotAction, AvailableActions, ActionChoice, ApiResponse
from rlbot_twitch_broker_client import Configuration, RegisterApi, ApiClient, ActionServerRegistration
from rlbot_twitch_broker_client.defaults import STANDARD_TWITCH_BROKER_PORT
from urllib3.exceptions import MaxRetryError
from util.orientation import Orientation, look_at_orientation
from util.vec import Vec3

FLIP_CAR = 'flipCar'
NUDGE_CAR = 'nudgeCar'
PLAYER_NAME = 'playerName'


class MyActionBroker(BotActionBroker):
    def __init__(self, script):
        self.script = script

    def get_actions_currently_available(self) -> List[AvailableActions]:
        return self.script.get_actions_currently_available()

    def set_action(self, choice: ActionChoice):
        self.script.process_choice(choice.action)
        return ApiResponse(200, f"The botherer shall {choice.action.description}")


def get_flipped_orientation(rotation: Rotator):
    orientation = Orientation(rotation)
    flipped = look_at_orientation(orientation.forward, orientation.up * -1)
    return flipped


class CarBotherer(BaseScript):

    def __init__(self):
        super().__init__("Car Botherer")
        self.action_broker = MyActionBroker(self)
        self.known_players: List[PlayerInfo] = []

    def heartbeat_connection_attempts_to_twitch_broker(self, port):
        register_api_config = Configuration()
        register_api_config.host = f"http://127.0.0.1:{STANDARD_TWITCH_BROKER_PORT}"
        twitch_broker_register = RegisterApi(ApiClient(configuration=register_api_config))
        while True:
            try:
                twitch_broker_register.register_action_server(
                    ActionServerRegistration(base_url=f"http://127.0.0.1:{port}"))
            except MaxRetryError:
                self.logger.warning('Failed to register with twitch broker, will try again...')
            sleep(10)

    def process_choice(self, choice: BotAction):
        player_index = self.get_player_index_by_name(choice.data[PLAYER_NAME])
        if player_index is not None:
            car = self.game_tick_packet.game_cars[player_index]
            if choice.action_type == FLIP_CAR:
                flipped = get_flipped_orientation(car.physics.rotation)
                self.set_game_state(
                    GameState(cars={player_index: CarState(physics=Physics(rotation=flipped.to_rotator()))}))
            if choice.action_type == NUDGE_CAR:
                car_vel = Vec3(car.physics.velocity)
                rand_vec = Vec3(random() - .5, random() - .5, 0).normalized()
                nudge_vel = Vector3(car_vel.x + rand_vec.x * 700, car_vel.y + rand_vec.y * 700, car_vel.z + 500)
                self.set_game_state(
                    GameState(cars={player_index: CarState(physics=Physics(velocity=nudge_vel))}))

    def start(self):
        port = find_usable_port(9817)
        Thread(target=run_action_server, args=(port,), daemon=True).start()
        set_bot_action_broker(self.action_broker)  # This seems to only work after the bot hot reloads once, weird.

        Thread(target=self.heartbeat_connection_attempts_to_twitch_broker, args=(port,), daemon=True).start()

        while True:
            packet = self.get_game_tick_packet()
            raw_players = [self.game_tick_packet.game_cars[i]
                           for i in range(packet.num_cars)]
            self.known_players = [p for p in raw_players if p.name]
            sleep(0.5)

    def get_player_index_by_name(self, name: str):
        for i in range(self.game_tick_packet.num_cars):
            car = self.game_tick_packet.game_cars[i]
            if car.name == name:
                return i
        return None

    def get_actions_currently_available(self) -> List[AvailableActions]:
        actions = []
        for player in self.known_players:
            actions.append(BotAction(description=f'Flip {highlight_player_name(player)}', action_type=FLIP_CAR,
                                     data={PLAYER_NAME: player.name}))
            actions.append(BotAction(description=f'Nudge {highlight_player_name(player)}', action_type=NUDGE_CAR,
                                     data={PLAYER_NAME: player.name}))

        return [AvailableActions("Car Botherer", None, actions)]


if __name__ == '__main__':
    car_botherer = CarBotherer()
    car_botherer.start()
