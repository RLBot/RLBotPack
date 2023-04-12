import csv
import random

from rlbot.agents.base_loadout_generator import BaseLoadoutGenerator
from rlbot.csv.items import get_items_path
from rlbot.matchconfig.loadout_config import LoadoutConfig


def generate_items_dict():
    items_dict = dict()
    with open(get_items_path(), 'r') as f:
        csv_reader = csv.reader(f)
        for item in csv_reader:
            # 0: id, 1: type, 2: useless garbage, 3: name
            if item[3].find("Mystery") == -1 and item[3].find("Import") == -1:
                if item[1] not in items_dict:
                    items_dict[item[1]] = [item]
                else:
                    items_dict[item[1]].append(item)
    return items_dict


def decal_picker(body_string, items_dict):
    special_body_suffixes = ["Type-S", "GT", "ZSR", "XL", "RX-T", "Mk-2", "GXT"]
    suitable_decals = []
    for decal in items_dict["Skin"]:
        if decal[3].find(body_string) != -1:
            for suffix in special_body_suffixes:
                if decal[3][len(body_string):].find(suffix) != -1:
                    break
            else:
                suitable_decals.append(decal)
        else:
            for body in items_dict["Body"]:
                if decal[3].find(body[3]) != -1:
                    break
            else:
                suitable_decals.append(decal)
    return int(random.choice(suitable_decals)[0])


def make_base_picks(items: dict, loadout_file: LoadoutConfig):
    loadout_file.team_color_id = random.randint(0, 69)
    loadout_file.custom_color_id = random.randint(0, 104)
    body = random.choice(items["Body"])
    loadout_file.car_id = int(body[0])
    loadout_file.decal_id = int(decal_picker(body[3], items))
    loadout_file.antenna_id = int(random.choice(items["Antenna"])[0])
    loadout_file.wheels_id = int(random.choice(items["Wheels"])[0])
    loadout_file.boost_id = int(random.choice(items["Boost"])[0])
    loadout_file.hat_id = int(random.choice(items["Hat"])[0])
    loadout_file.engine_audio_id = int(random.choice(items["EngineAudio"])[0])
    loadout_file.trails_id = int(random.choice(items["SupersonicTrail"])[0])
    loadout_file.goal_explosion_id = int(random.choice(items["GoalExplosion"])[0])


def make_item_color_picks(loadout: LoadoutConfig):
    loadout.paint_config.car_paint_id = random.randint(0, 13)
    loadout.paint_config.decal_paint_id = random.randint(0, 13)
    loadout.paint_config.wheels_paint_id = random.randint(0, 13)
    loadout.paint_config.boost_paint_id = random.randint(0, 13)
    loadout.paint_config.antenna_paint_id = random.randint(0, 13)
    loadout.paint_config.hat_paint_id = random.randint(0, 13)
    loadout.paint_config.trails_paint_id = random.randint(0, 13)
    loadout.paint_config.goal_explosion_paint_id = random.randint(0, 13)


class RandomLoadoutGenerator(BaseLoadoutGenerator):
    def generate_loadout(self, player_index: int, team: int) -> LoadoutConfig:
        loadout = LoadoutConfig()
        #loadout = self.load_cfg_file(Path('stock_appearance.cfg'), team)
        items = generate_items_dict()
        make_base_picks(items, loadout)
        make_item_color_picks(loadout)

        return loadout


if __name__ == "__main__":
    RandomLoadoutGenerator.generate_loadout(1,1,1)
