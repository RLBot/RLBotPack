import math
from typing import List, Set, Optional

from maneuvers.driving.travel import Travel
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, norm
from rlutilities.simulation import Car, Pad
from tools.drawing import DrawingTool
from tools.game_info import GameInfo
from tools.intercept import estimate_time
from tools.vector_math import distance


class Refuel(Maneuver):
    """
    Choose a large boost pad and go pick it up.
    """

    def __init__(self, car: Car, info: GameInfo, forbidden_pads: Set[Pad] = set()):
        super().__init__(car)
        self.info = info

        pads = set(info.large_boost_pads) - forbidden_pads
        pickupable_pads = {pad for pad in pads if pad.is_active or estimate_time(car, pad.position) * 0.8 > pad.timer}
        pos = (info.ball.position + car.position * 2 + info.my_goal.center) / 4
        self.pad = min(pickupable_pads, key=lambda pad: distance(pad.position, pos)) if pickupable_pads else None

        self.pad_was_active = self.pad and self.pad.is_active

        self.travel = Travel(car, self.pad.position if self.pad else info.my_goal.center, waste_boost=True)

    @staticmethod
    def best_boostpad_to_pickup(car: Car, pads: Set[Pad], pos: vec3) -> Optional[Pad]:
        best_pad = None
        best_dist = math.inf

        for pad in pads:
            dist = distance(pos, pad.position)
            time_estimate = estimate_time(car, pad.position) * 0.7

            if dist < best_dist and (pad.is_active or pad.timer < time_estimate):
                best_pad = pad
                best_dist = dist

        return best_pad

    def interruptible(self) -> bool:
        return self.travel.interruptible()

    def step(self, dt):
        if self.pad is None:
            self.finished = True
            return

        # slow down when we're about to pick up the boost, so we can turn faster afterwards
        if distance(self.car, self.pad) < norm(self.car.velocity) * 0.2:
            self.travel.drive.target_speed = 1400

        self.travel.step(dt)
        self.controls = self.travel.controls

        # finish when someone picks up the pad
        if not self.pad.is_active and self.pad_was_active:
            self.finished = True
        self.pad_was_active = self.pad.is_active

        # finish when we picked the boost up but the previous condition somehow wasn't true
        if self.car.boost > 99 or distance(self.car, self.pad) < 100:
            self.finished = True

    def render(self, draw: DrawingTool):
        self.travel.render(draw)

        if self.pad and not self.pad.is_active:
            draw.color(draw.yellow)
            draw.string(self.pad.position + vec3(0, 0, 100), int(self.pad.timer*100)/100)
