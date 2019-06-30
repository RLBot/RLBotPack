from maneuvers.kit import *

from RLUtilities.Maneuvers import Aerial as RLUAerial

class Aerial(RLUAerial):

    def step(self, dt):
        super().step(dt)
        if self.total_timer > 1 and self.car.on_ground:
            self.finished = True

    def render(self, draw: DrawingTool):
        draw.color(draw.yellow)
        draw.car_trajectory(self.car, self.t_arrival)
        draw.color(draw.lime)
        draw.point(self.target)