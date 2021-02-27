

from typing import List

from rlbot.agents.base_agent import SimpleControllerState
from tmcp import TMCPMessage

from maneuvers.maneuver import Maneuver
from utility.info import BoostPad
from utility.vec import norm, proj_onto_size


class CollectClosestBoostManeuver(Maneuver):
    def __init__(self, bot, pads: List[BoostPad]=None, target_vel: int=2200):
        super().__init__()
        self.time_begin = bot.info.time
        self.announced_in_tmcp = False
        self.target_vel = target_vel

        self.target_pad = None

        if pads is None:
            pads = bot.info.big_boost_pads

        self.pick_pad(bot, pads)

    def pick_pad(self, bot, pads: List[BoostPad]):
        # Find closest boost pad
        my_pos = bot.info.my_car.pos
        shortest_dist = 99999999
        for pad in pads:
            if pad.is_active:
                dist = norm(my_pos - pad.pos)
                if dist < shortest_dist:
                    self.target_pad = pad
                    shortest_dist = dist


    def exec(self, bot) -> SimpleControllerState:
        car = bot.info.my_car

        # Somehow we didn't find a good pad
        if self.target_pad is None:
            self.done = True
            return SimpleControllerState()

        # Since this maneuver is stopped early, we make sure some time pass before announcing. This prevents spam
        if not self.announced_in_tmcp and self.time_begin + 0.1 < bot.info.time:
            self.announced_in_tmcp = True
            bot.send_tmcp(TMCPMessage.boost_action(bot.team, bot.index, self.target_pad.index))

        # End maneuver when almost there or pad becomes inactive
        car_to_pad = self.target_pad.pos - car.pos
        vel = proj_onto_size(car.vel, car_to_pad)
        dist = norm(car_to_pad)
        if dist < 50 + vel * 0.2 or car.boost > 50 or not self.target_pad.is_active:
            self.done = True

        bot.renderer.draw_line_3d(car.pos, self.target_pad.pos, bot.renderer.yellow())
        return bot.drive.towards_point(bot, self.target_pad.pos, target_vel=self.target_vel, slide=True, boost_min=0, can_dodge=self.target_pad.is_big)


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
