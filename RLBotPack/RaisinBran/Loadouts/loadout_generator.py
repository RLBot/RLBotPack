import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig

# Randomly chooses a loadout config file from the loadouts folder!

class RandomLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        
        # Creates a list of all the loadout files in the loadouts folder
        loadouts_folder = self.base_directory / 'loadouts'
        loadout_list = [f for f in loadouts_folder.glob("*.cfg") if f.is_file()]

        # Chooses a random loadout file from the list, and applies it to our bot! :D
        choice = random.randrange(0, len(loadout_list))
        loadout = self.load_cfg_file(loadout_list[choice], team)

        return loadout