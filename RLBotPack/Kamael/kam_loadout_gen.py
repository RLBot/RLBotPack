import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SimpleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:

        if player_index == 0 and team == 0 or player_index == 1 and team == 1 or player_index==3 and team == 1:
            return self.load_cfg_file(Path('loadouts/kam_original.cfg'), team)
        else:

            choice = random.randrange(0,3)
            if choice == 1:
                loadout = self.load_cfg_file(Path('loadouts/kam_breakout.cfg'), team)
            elif choice == 2:
                loadout = self.load_cfg_file(Path('loadouts/kam_dom.cfg'), team)

            else:
                loadout = self.load_cfg_file(Path('loadouts/kam_original.cfg'), team)

            return loadout