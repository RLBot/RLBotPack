from maneuvers.kit import *

from maneuvers.driving.travel import Travel


class Refuel(Maneuver):
    def __init__(self, car: Car, info: GameInfo, target: vec3):
        super().__init__(car)
        self.info = info

        pos = (target + car.position * 2 + info.my_goal.center * 2) / 5
        self.pad = self.nearest_boostpad(car, info, pos)
        self.travel = Travel(car, self.pad.position, waste_boost=True)

    @staticmethod
    def nearest_boostpad(car: Car, info: GameInfo, pos: vec3):
        best_pad = None
        best_dist = 9999
        for pad in info.large_boost_pads:
            if pad.is_full_boost:
                dist = distance(pos, pad.position)
                if (pad.is_active or pad.timer < estimate_time(car, pad.position, estimate_max_car_speed(car))) and dist < best_dist:
                    best_pad = pad
                    best_dist = dist
        return best_pad

    def step(self, dt):
        if norm(self.car.velocity) > 1400:
            if distance(self.car, self.pad) < norm(self.car.velocity) * 0.2:
                self.travel.action.target_speed = 1300
        self.travel.step(dt)
        self.controls = self.travel.controls
        self.finished = (not self.pad.is_active \
        and not self.pad.timer < estimate_time(self.car, self.pad.position, estimate_max_car_speed(self.car))) \
        or self.car.boost > 99

    def render(self, draw: DrawingTool):
        self.travel.render(draw)