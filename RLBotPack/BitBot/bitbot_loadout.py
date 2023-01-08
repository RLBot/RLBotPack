import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig




class LoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('appearance.cfg'), team)

        """
        Dingo - 5361
        Dominus - 403
        """
        loadout.car_id = random.choice((5361, 403))

        return loadout