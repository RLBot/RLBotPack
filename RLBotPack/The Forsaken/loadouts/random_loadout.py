import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SampleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        # You could start with a loadout based on a cfg file in the same directory as this generator
        loadouts = [self.load_cfg_file(Path('./loadouts/Dragon_app.cfg'), team),
                    self.load_cfg_file(Path('./loadouts/Fire_app.cfg'), team),
                    self.load_cfg_file(Path('./loadouts/Forsaken_app.cfg'), team),
                    self.load_cfg_file(Path('./loadouts/Lanfear_app.cfg'), team),
                    self.load_cfg_file(Path('./loadouts/Dragon_app.cfg'), team),
                    self.load_cfg_file(Path('./loadouts/Dragon_app.cfg'), team)]
        return random.choice(loadouts)
