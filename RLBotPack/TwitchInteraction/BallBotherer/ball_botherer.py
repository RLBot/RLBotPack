from random import random
from threading import Thread
from typing import List

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, Physics, Vector3, BallState
from rlbot.utils.structures.game_data_struct import PlayerInfo
from rlbot_action_server.bot_action_broker import BotActionBroker, run_action_server, find_usable_port
from rlbot_action_server.bot_holder import set_bot_action_broker
from rlbot_action_server.models import BotAction, AvailableActions, ActionChoice, ApiResponse
from rlbot_twitch_broker_client import Configuration, RegisterApi, ApiClient, ActionServerRegistration
from rlbot_twitch_broker_client.defaults import STANDARD_TWITCH_BROKER_PORT
from time import sleep
from urllib3.exceptions import MaxRetryError

from util.vec import Vec3

FREEZE = 'freeze'
NUDGE = 'nudgeball'

class MyActionBroker(BotActionBroker):
    def __init__(self, script):
        self.script = script

    def get_actions_currently_available(self) -> List[AvailableActions]:
        return self.script.get_actions_currently_available()

    def set_action(self, choice: ActionChoice):
        self.script.process_choice(choice.action)
        return ApiResponse(200, f"The botherer shall {choice.action.description}")



class BallBotherer(BaseScript):

    def __init__(self):
        super().__init__("Ball Botherer")
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

        if choice.action_type == FREEZE:
            for i in range(5):
                self.set_game_state(
                    GameState(ball=BallState(physics=Physics(velocity=Vector3(0, 0, 0)))))
                sleep(.1)
            return

        if choice.action_type == NUDGE:
            ball_vel = self.game_tick_packet.game_ball.physics.velocity
            rand_vec = Vec3(random() - .5, random() - .5, random() - .5).rescale(1000)
            self.set_game_state(
                GameState(ball=BallState(physics=Physics(velocity=Vector3(rand_vec.x + ball_vel.x, rand_vec.y + ball_vel.y, rand_vec.z + ball_vel.z)))))
            return


    def start(self):
        port = find_usable_port(7512)
        Thread(target=run_action_server, args=(port,), daemon=True).start()
        set_bot_action_broker(self.action_broker)  # This seems to only work after the bot hot reloads once, weird.

        Thread(target=self.heartbeat_connection_attempts_to_twitch_broker, args=(port,), daemon=True).start()

        while True:
            self.get_game_tick_packet()
            sleep(0.5)

    def get_actions_currently_available(self) -> List[AvailableActions]:
        actions = []
        actions.append(BotAction(description="Freeze ball", action_type=FREEZE))
        actions.append(BotAction(description="Nudge ball", action_type=NUDGE))
        return [AvailableActions("Ball Botherer", None, actions)]


if __name__ == '__main__':
    ball_botherer = BallBotherer()
    ball_botherer.start()
