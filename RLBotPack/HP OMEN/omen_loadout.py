import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig




class LoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('appearance.cfg'), team)

        """
        F150 - 5713
        Mustang - 6836
        """
        loadout.car_id = random.choice((5713, 6836))

        return loadout