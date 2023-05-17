import importlib
import time
import traceback
from pathlib import Path
from types import ModuleType

from rlbot.agents.base_script import BaseScript
from rlbot.matchconfig.loadout_config import LoadoutConfig
from rlbot.matchconfig.match_config import PlayerConfig, MatchConfig, MutatorConfig
from rlbot.parsing.match_settings_config_parser import game_map_dict
from rlbot.setup_manager import SetupManager

import quantum_league


def human_config():
    player_config = PlayerConfig()
    player_config.bot = False
    player_config.team = 0
    player_config.name = "Human"
    return player_config


def create_player_config(name: str, team):
    player_config = PlayerConfig()
    player_config.bot = True
    player_config.rlbot_controlled = True
    player_config.name = name
    player_config.team = team
    player_config.loadout_config = LoadoutConfig()
    player_config.loadout_config.team_color_id = 26
    return player_config


def build_match_config(game_map="Mannfield_Night"):
    match_config = MatchConfig()
    match_config.player_configs = [create_player_config("You", i % 2) for i in range(20)] + [human_config()]

    match_config.game_mode = "Soccer"
    match_config.game_map = game_map

    match_config.mutators = MutatorConfig()
    # match_config.mutators.boost_amount = "Unlimited"
    match_config.mutators.match_length = "Unlimited"
    match_config.mutators.respawn_time = "Disable Goal Reset"
    match_config.mutators.demolish = "Disabled"

    match_config.enable_state_setting = True
    match_config.enable_rendering = True

    match_config.existing_match_behavior = "Restart"
    match_config.instant_start = True

    return match_config


class MinigameRunner(BaseScript):
    def __init__(self):
        super().__init__("Quantum League")
        self.setup_manager = SetupManager()
        self.setup_manager.game_interface = self.game_interface

        current_game_map = int(self.game_interface.get_match_settings().GameMap())
        current_game_map = list(game_map_dict.keys())[current_game_map]

        # copied this from TrackAndField, without this rlbot crashes for some reason
        self.setup_manager.num_participants = 0
        self.setup_manager.launch_bot_processes(MatchConfig())

        self.setup_manager.load_match_config(build_match_config(current_game_map))
        self.setup_manager.start_match()

        while True:
            packet = self.wait_game_tick_packet()
            if packet.game_info.is_round_active:
                break
        self.minigame = quantum_league.QuantumLeague(self.game_interface, packet)

        self.minigame_file = Path(__file__).parent / "quantum_league.py"
        self.last_mtime = self.minigame_file.lstat().st_mtime

    def run(self):
        while True:
            packet = self.wait_game_tick_packet()

            # hot reload
            mtime = self.minigame_file.lstat().st_mtime
            if mtime > self.last_mtime:
                try:
                    importlib.reload(quantum_league)
                    self.minigame = quantum_league.QuantumLeague(self.game_interface, packet)
                    print(f"[{mtime}] Reloaded minigame")
                    self.last_mtime = mtime

                except Exception as ex:
                    print()
                    print("-----------------RELOAD EXCEPTION-----------------")
                    print(ex)
                    print(traceback.format_exc())

            try:
                self.minigame.step(packet)

            except Exception as ex:
                print()
                print("-----------------STEP EXCEPTION-----------------")
                print(ex)
                print(traceback.format_exc())

                time.sleep(1.0)
                continue


if __name__ == '__main__':
    script = MinigameRunner()
    script.run()
