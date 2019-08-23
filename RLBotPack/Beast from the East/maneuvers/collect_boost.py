

from typing import List

from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.maneuver import Maneuver
from util.info import BoostPad
from util.vec import norm, proj_onto_size


class CollectClosestBoostManeuver(Maneuver):
    def __init__(self, bot, pads: List[BoostPad]=None, target_vel: int=2200):
        super().__init__()

        self.target_vel = target_vel

        self.closest_pad = None

        if pads is None:
            pads = bot.info.big_boost_pads

        # Find closest boost pad
        my_pos = bot.info.my_car.pos
        shortest_dist = 99999999
        for pad in pads:
            dist = norm(my_pos - pad.pos)
            if dist < shortest_dist:
                self.closest_pad = pad
                shortest_dist = dist

    def exec(self, bot) -> SimpleControllerState:
        car = bot.info.my_car

        # End maneuver when almost there
        car_to_pad = self.closest_pad.pos - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < 50 + vel * 0.2 or car.boost > 50:
            self.done = True

        bot.renderer.draw_line_3d(car.pos, self.closest_pad.pos, bot.renderer.yellow())
        return bot.drive.go_towards_point(bot, self.closest_pad.pos, target_vel=2200, slide=True, boost_min=0)


def filter_pads(bot, pads: List[BoostPad], big_only=True, my_side=True, center=True, enemy_side=True):
    return [
        pad for pad in pads if
        (not big_only or (big_only and pad.is_big))
        and (
            (my_side and 1000 < pad.pos.y * bot.info.team_sign)
            or
            (center and -1000 < pad.pos.y * bot.info.team_sign < 1000)
            or
            (enemy_side and pad.pos.y * bot.info.team_sign < -1000)
        )
    ]
