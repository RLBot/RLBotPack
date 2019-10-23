from maneuvers.dribbling.dribble import Dribble
from maneuvers.air.aerial import Aerial
from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.strike import Strike
from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.mirror_shot import MirrorShot
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.aerial_shot import AerialShot
from maneuvers.strikes.wall_shot import WallShot
from maneuvers.strikes.wall_dodge_shot import WallDodgeShot
from maneuvers.shadow_defense import ShadowDefense
from utils.game_info import GameInfo


def get_maneuver_by_name(name: str, info: GameInfo):
    if name == "DodgeShot":
        return DodgeShot(info.my_car, info, info.their_goal.center)