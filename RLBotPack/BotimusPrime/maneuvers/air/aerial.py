from maneuvers.kit import *

from rlutilities.mechanics import Aerial as RLUAerial

class Aerial(RLUAerial):
    '''Wrapper for the RLU Aerial class'''
    
    def step(self, dt):
        super().step(dt)

        # abort if failed to take off
        # if self. > 0.5 and self.car.on_ground:
        #     self.finished = True

    def render(self, draw: DrawingTool):
        draw.color(draw.yellow)
        draw.car_trajectory(self.car, self.arrival_time)
        draw.color(draw.lime)
        draw.point(self.target)