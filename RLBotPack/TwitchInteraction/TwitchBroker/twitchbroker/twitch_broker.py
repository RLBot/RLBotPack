import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from threading import Thread
from typing import List, Dict

from rlbot.agents.base_script import BaseScript
from rlbot.utils.game_state_util import GameState, GameInfoState
from rlbot_action_client import Configuration, ActionApi, ApiClient, ActionChoice
from twitchbroker.action_and_server_id import AvailableActionsAndServerId
from twitchbroker.overlay_data import OverlayData, serialize_for_overlay, generate_menu_id, generate_menu, \
    CommandAcknowledgement, VoteTracker
from rlbot_twitch_broker_client.models.chat_line import ChatLine
from rlbot_twitch_broker_server import chat_buffer
from rlbot_twitch_broker_server import client_registry
from rlbot_twitch_broker_server.client_registry import ActionServerData
from rlbot_twitch_broker_server.run import find_usable_port, run_twitch_broker_server
from time import sleep
from twitchio import Message
from twitchio.ext.commands import Bot as TwitchBot


class AvailableActionAggregator:
    def __init__(self):
        self.action_apis: Dict[str, ActionApi] = {}

    def make_action_api(self, client_data: ActionServerData):
        bot_action_api_config = Configuration()
        bot_action_api_config.host = client_data.base_url
        return ActionApi(ApiClient(configuration=bot_action_api_config))

    def fetch_all(self) -> List[AvailableActionsAndServerId]:
        registry = client_registry.CLIENT_REGISTRY
        request_threads = []
        combined_actions: List[AvailableActionsAndServerId] = []
        try:
            for client in list(registry.clients.values()):
                if client.base_url not in self.action_apis:
                    self.action_apis[client.get_key()] = self.make_action_api(client)

                action_api = self.action_apis[client.get_key()]

                request_threads.append((client.get_key(), action_api.get_actions_currently_available(
                    async_req=True, _request_timeout=0.2)))

            for (client_key, req) in request_threads:
                avail_actions_list = req.get()
                combined_actions += [AvailableActionsAndServerId(a, client_key) for a in avail_actions_list]
        except Exception as e:
            print(e)
        return combined_actions

    def get_action_api(self, action_server_id):
        return self.action_apis[action_server_id]


@dataclass
class TwitchAuth:
    username: str
    oauth: str
    channel: str


class TwitchChatAdapter(TwitchBot):
    def __init__(self, twitch_auth: TwitchAuth):
        super().__init__(nick=twitch_auth.username, irc_token=twitch_auth.oauth, initial_channels=[twitch_auth.channel], prefix='!rlb')

    async def event_message(self, message: Message):
        chat_buffer.CHAT_BUFFER.enqueue_chat(ChatLine(username=message.author.display_name, message=message.content))


@dataclass
class MutableBrokerSettings:
    num_old_menus_to_honor: int = 0
    pause_on_menu: bool = False
    play_time_between_pauses: int = 5
    votes_needed: Dict[str, int] = field(default_factory=dict)


class TwitchBroker(BaseScript):

    def __init__(self, overlay_folder: Path, twitch_auth: TwitchAuth, broker_settings: MutableBrokerSettings):
        super().__init__('TwitchBroker')
        self.json_file = overlay_folder / 'twitch_broker_overlay.json'
        self.chat_buffer = chat_buffer.CHAT_BUFFER
        self.menu_id = None
        self.twitch_chat_adapter = None
        self.broker_settings = broker_settings
        self.vote_trackers: Dict[str, VoteTracker] = {}
        self.recent_menus: List[OverlayData] = []
        self.needs_new_menu = True
        self.aggregator = AvailableActionAggregator()
        self.recent_commands: List[CommandAcknowledgement] = []
        self.stop_list = set()
        self.command_count = 0
        self.next_menu_moment: float = 0
        if twitch_auth:
            self.twitch_chat_adapter = TwitchChatAdapter(twitch_auth)
            twitch_thread = Thread(target=self.twitch_chat_adapter.run)
            twitch_thread.setDaemon(True)
            twitch_thread.start()

    def write_json_for_overlay(self, overlay_data: OverlayData):
        json_string = json.dumps(overlay_data, default=serialize_for_overlay)
        self.json_file.write_text(json_string)

    def run_loop_with_chat_buffer(self, desired_port: int):
        port = find_usable_port(desired_port)
        broker_server_thread = Thread(target=run_twitch_broker_server, args=(port,))
        broker_server_thread.setDaemon(True)
        broker_server_thread.start()
        client_registry.CLIENT_REGISTRY = client_registry.ActionServerRegistry()

        while True:
            self.get_game_tick_packet()
            self.ensure_action_menu()
            self.process_chat()
            # self.make_passive_overlay_updates()

            sleep(.1)

    def ensure_action_menu(self):
        if not self.needs_new_menu:
            return

        if not self.game_tick_packet.game_info.is_round_active:
            if self.broker_settings.pause_on_menu:
                # This seems like overkill, but we keep getting in annoying situations during replays.
                self.set_game_state(GameState(game_info=GameInfoState(game_speed=1)))
            return

        if self.game_tick_packet.game_info.seconds_elapsed < self.next_menu_moment:
            return

        all_actions = self.aggregator.fetch_all()

        self.menu_id = generate_menu_id()
        overlay_data = generate_menu(all_actions, self.menu_id, self.recent_commands, self.game_tick_packet,
                                     self.vote_trackers)

        if overlay_data.num_actions() == 0:
            return

        if self.broker_settings.pause_on_menu:
            self.set_game_state(GameState(game_info=GameInfoState(game_speed=0.01)))

        self.write_json_for_overlay(overlay_data)
        # TODO: consider notifying twitch chat of the new prefix via bot in twitch chat for reduced round trip latency
        # TODO: also look into twitch extensions: https://dev.twitch.tv/extensions

        self.recent_menus.insert(0, overlay_data)
        if len(self.recent_menus) > self.broker_settings.num_old_menus_to_honor + 1:
            killed_menu = self.recent_menus.pop()
            expired_vote_tracker_keys = [key for key, tracker in self.vote_trackers.items() if tracker.original_menu_id == killed_menu.menu_id]
            for expired_vt_key in expired_vote_tracker_keys:
                self.vote_trackers.pop(expired_vt_key)
        self.needs_new_menu = False

    def process_chat(self):
        if not self.game_tick_packet.game_info.is_round_active:
            self.vote_trackers.clear()
            return

        if not self.chat_buffer.has_chat():
            return

        chat_line = self.chat_buffer.dequeue_chat()
        text = chat_line.message
        for menu_index, menu in enumerate(self.recent_menus):
            match = re.search(menu.menu_id + '([0-9]+)', text, re.IGNORECASE)
            if match is None:
                continue
            stop_string = f'{match.group(0)}{chat_line.username}'
            if stop_string not in self.stop_list:
                choice_num = int(match.group(1))
                choice = menu.retrieve_choice(choice_num)
                if not choice:
                    print(f"Invalid choice number {choice_num}")
                    continue
                votes_needed_key = choice.entity_name.lower()
                if votes_needed_key in self.broker_settings.votes_needed:
                    votes_needed = self.broker_settings.votes_needed[votes_needed_key]
                    if votes_needed > 1:
                        if choice.bot_action.description not in self.vote_trackers:
                            self.vote_trackers[choice.bot_action.description] = VoteTracker(votes_needed, menu.menu_id, [])
                        vote_tracker = self.vote_trackers[choice.bot_action.description]
                        vote_tracker.register_vote(chat_line.username)
                        self.write_json_for_overlay(self.recent_menus[0])
                        if not vote_tracker.has_needed_votes():
                            continue
                        # Vote successful! Clear out the vote tracker.
                        self.vote_trackers.pop(choice.bot_action.description)
                action_api = self.aggregator.get_action_api(choice.action_server_id)
                self.command_count += 1
                try:
                    result = action_api.choose_action(
                        ActionChoice(action=choice.bot_action, entity_name=choice.entity_name))
                    status = "success" if result.code == 200 else "error"
                    description = choice.bot_action.description if result.code == 200 else result.reason
                    self.recent_commands.append(
                        CommandAcknowledgement(chat_line.username, description, status, str(self.command_count)))
                    if result.code == 200:
                        self.stop_list.add(stop_string)
                except Exception as e:
                    self.recent_commands.append(
                        CommandAcknowledgement(chat_line.username, str(e), "error", str(self.command_count)))
                    print(e)
                if len(self.recent_commands) > 10:
                    self.recent_commands.pop(0)  # Get rid of the oldest command

                # This causes the new command acknowledgement to get published. The overlay_data has an
                # internal reference to recent_commands.
                self.write_json_for_overlay(self.recent_menus[0])
                if menu_index == 0:
                    self.needs_new_menu = True
                    if self.broker_settings.pause_on_menu:
                        self.set_game_state(GameState(game_info=GameInfoState(game_speed=1)))
                        self.next_menu_moment = self.game_tick_packet.game_info.seconds_elapsed + self.broker_settings.play_time_between_pauses
                break
