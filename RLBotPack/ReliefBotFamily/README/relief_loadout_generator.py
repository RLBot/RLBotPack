import colorsys
from pathlib import Path

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.matchconfig.loadout_config import LoadoutConfig, Color


class ReliefBotLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:

        # You could start with a loadout based on a cfg file in the same directory as this generator
        loadout = self.load_cfg_file(Path('relief_bot_appearance.cfg'), team)

        if team == 0:
            paints = [4, 5, 7]
            hues = [0.55, 0.6, 0.4]
        else:
            paints = [1, 6, 10]
            hues = [0, 0.1, 0.13]

        paint_id = paints[player_index % 3]

        rgb = colorsys.hsv_to_rgb(hues[player_index % 3], 1, 0.6)
        loadout.primary_color_lookup = Color(float_to_byte(rgb[0]), float_to_byte(rgb[1]), float_to_byte(rgb[2]), 255)

        loadout.paint_config.wheels_paint_id = paint_id
        loadout.paint_config.trails_paint_id = paint_id

        return loadout


def float_to_byte(value: float) -> int:
    return int(value * 255)
