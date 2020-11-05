import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SimpleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:

        # if player_index == 0 or player_index == 3:
        #     #return self.load_cfg_file(Path('loadouts/kam_gizmo.cfg'), team)
        #     return self.load_cfg_file(Path('loadouts/kam_dom.cfg'), team)
        # elif player_index == 1 or player_index == 4:
        #     return self.load_cfg_file(Path('loadouts/kam_octane.cfg'), team)
        # elif player_index == 2 or player_index == 5 or player_index == 3 or player_index == 6:
        #     return self.load_cfg_file(Path('loadouts/kam_marauder.cfg'), team)
        # else:
        choice = random.randrange(0, 3)
        if choice == 1:
            loadout = self.load_cfg_file(Path("loadouts/kam_gizmo.cfg"), team)
        elif choice == 2:
            # loadout = self.load_cfg_file(Path('loadouts/kam_octane.cfg'), team)
            loadout = self.load_cfg_file(Path("loadouts/kam_dom.cfg"), team)
        else:
            # loadout = self.load_cfg_file(Path('loadouts/kam_marauder.cfg'), team)
            loadout = self.load_cfg_file(Path("loadouts/kam_octane.cfg"), team)

        return loadout
