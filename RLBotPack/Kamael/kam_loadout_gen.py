import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SimpleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:

        choice = random.randint(0,100)
        if choice < 50 :
            loadout = self.load_cfg_file(Path("loadouts/kam_gizmo.cfg"), team)
        elif choice < 99:
            # loadout = self.load_cfg_file(Path('loadouts/kam_octane.cfg'), team)
            loadout = self.load_cfg_file(Path("loadouts/kam_octane.cfg"), team)
        else:
            # loadout = self.load_cfg_file(Path('loadouts/kam_marauder.cfg'), team)
            loadout = self.load_cfg_file(Path("loadouts/kam_dom.cfg"), team)


        return loadout
