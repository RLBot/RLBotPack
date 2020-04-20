import random
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig


class SampleLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:

        # You could start with a loadout based on a cfg file in the same directory as this generator
        loadout = self.load_cfg_file(Path('appearance.cfg'), team)

        # Or you could start from scratch like this
        # loadout = LoadoutConfig()

        if player_index >= 1 and player_index != 3:
            colour = random.randrange(0, 70)
            while (colour == 67 and team == 0) or (colour == 36 and team == 1):
                colour = random.randrange(0, 70)
            loadout.antenna_id = random.choice([186, 128])  # use a Psyonix flag if you're the first player
            loadout.team_color_id = colour  # Different primary color depending on player index
            mod = colour % 10
            if team == 0:
                if mod == 0:
                    loadout.paint_config.goal_explosion_paint_id = 2
                    loadout.paint_config.trails_paint_id = 2
                    loadout.paint_config.boost_paint_id = 2
                elif 1 <= mod <= 2:
                    loadout.paint_config.goal_explosion_paint_id = 7
                    loadout.paint_config.trails_paint_id = 7
                    loadout.paint_config.boost_paint_id = 7
                elif 3 <= mod <= 4:
                    loadout.paint_config.goal_explosion_paint_id = 4
                    loadout.paint_config.trails_paint_id = 4
                    loadout.paint_config.boost_paint_id = 4
                elif 5 <= mod <= 7:
                    loadout.paint_config.goal_explosion_paint_id = 5
                    loadout.paint_config.trails_paint_id = 5
                    loadout.paint_config.boost_paint_id = 5
                else:
                    loadout.paint_config.goal_explosion_paint_id = 8
                    loadout.paint_config.trails_paint_id = 8
                    loadout.paint_config.boost_paint_id = 8
            if team == 1:
                if 0 <= mod <= 1:
                    loadout.paint_config.goal_explosion_paint_id = 13
                    loadout.paint_config.trails_paint_id = 13
                    loadout.paint_config.boost_paint_id = 13
                elif 2 <= mod <= 5:
                    loadout.paint_config.goal_explosion_paint_id = 10
                    loadout.paint_config.trails_paint_id = 10
                    loadout.paint_config.boost_paint_id = 10
                elif 6 <= mod <= 7:
                    loadout.paint_config.goal_explosion_paint_id = 1
                    loadout.paint_config.trails_paint_id = 1
                    loadout.paint_config.boost_paint_id = 1
                else:
                    loadout.paint_config.goal_explosion_paint_id = 9
                    loadout.paint_config.trails_paint_id = 9
                    loadout.paint_config.boost_paint_id = 9


        return loadout