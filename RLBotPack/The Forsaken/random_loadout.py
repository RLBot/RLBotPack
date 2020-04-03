import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SampleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        # You could start with a loadout based on a cfg file in the same directory as this generator
        loadouts = [self.load_cfg_file(Path('Dragon_app.cfg'), team), self.load_cfg_file(Path('Fire_app.cfg'), team),
                    self.load_cfg_file(Path('Forsaken_app.cfg'), team),
                    self.load_cfg_file(Path('Lanfear_app.cfg'), team), self.load_cfg_file(Path('Dragon_app.cfg'), team),
                    self.load_cfg_file(Path('Dragon_app.cfg'), team)]
        return random.choice(loadouts)
