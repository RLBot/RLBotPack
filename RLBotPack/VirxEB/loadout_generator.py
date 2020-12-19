import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class LoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('appearance.cfg'), team)

        """
        Octane - 23 - Weight: 3
        Gizmo - 26
        Merc - 30 - Weight - 2
        Takumi - 402
        Marauder - 1172
        Takumi RX-T - 1295
        Vulcan - 1533
        Octane ZSR - 1568 - Weight - 2
        Twinzer - 2853
        Fennec - 4284 - Weight - 2
        """
        loadout.car_id = random.choice((23, 23, 23, 26, 30, 30, 402, 1172, 1295, 1533, 1568, 1568, 2853, 4284, 4284))

        # bots that don't have the stars decal will get the interstellar decal :D
        decal_id = {
            23: 305,
            26: 326,
            30: 348,
            402: 4989,
            1172: 4989,
            1295: 4989,
            1533: 4989,
            1568: 1747,  # Octane ZSR gets it's RLCS decal :D
            2853: 4989,
            4284: 4989
        }

        loadout.decal_id = decal_id[loadout.car_id]

        return loadout
