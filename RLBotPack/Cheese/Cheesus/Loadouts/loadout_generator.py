import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig

class RandomLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('default_appearance.cfg'), team)

        """
        Octane - 23
        Fennec - 4284
        Dingo - 5361
        """
        loadout.car_id = random.choice((23, 4284, 5361))

        return loadout