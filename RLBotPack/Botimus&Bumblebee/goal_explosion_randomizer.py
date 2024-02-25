import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig

SELECTION = [
    4373,  # Tactical Nuke
    3645,  # Lantern Rift
    3974,  # Force Razor
    4179,  # Voxel
    7485,  # Elemental
    7542,  # Shield Breaker
    5134,  # Spatial Rift
    9163,  # Optimus Prime :)
    8837,  # Chemergy
    5975,  # Phoenix Cannon
]


class GoalExplosionRandomizer(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('bumblebee-appearance.cfg'), team)
        loadout.goal_explosion_id = random.choice(SELECTION)
        return loadout