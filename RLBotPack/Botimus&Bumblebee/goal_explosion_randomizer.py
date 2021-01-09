import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig

SELECTION = [
    4373,  # Tactical Nuke
    3645,  # Lantern Rift
    4524,  # Meteor Storm
    3974,  # Force Razor
    4179,  # Voxel
    2702,  # Toon
]


class GoalExplosionRandomizer(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = self.load_cfg_file(Path('bumblebee-appearance.cfg'), team)
        loadout.goal_explosion_id = random.choice(SELECTION)
        return loadout