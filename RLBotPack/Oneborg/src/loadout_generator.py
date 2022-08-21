import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SampleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('appearance.cfg'), team)
        val = random.randint(1, 4)
        if val == 1:
            # Nimbus, Singularity, Nimbus: Fornax
            loadout.car_id = 3451
            loadout.goal_explosion_id = 3071
            loadout.decal_id = 3476
        elif val == 2:
            # Endo, Neuro-Agitator, Endo: Wings
            loadout.car_id = 1624
            loadout.goal_explosion_id = 4118
            loadout.decal_id = 1673
        elif val == 3:
            # R3MX, Supernova III, R3MX: Huntress
            loadout.car_id = 5470
            loadout.goal_explosion_id = 3131
            loadout.decal_id = 5523
        elif val == 4:
            # R3MX+, Shattered, R3MX: Huntress
            loadout.car_id = 5488
            loadout.goal_explosion_id = 3763
            loadout.decal_id = 5523
        return loadout