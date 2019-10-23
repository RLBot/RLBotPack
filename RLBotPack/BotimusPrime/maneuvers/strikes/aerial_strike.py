from maneuvers.kit import *

from maneuvers.strikes.strike import Strike
from maneuvers.driving.arrive import Arrive
from maneuvers.air.aerial import Aerial

from rlutilities.mechanics import AerialTurn

class AerialStrike(Strike):

    stop_updating = 1.5
    max_additional_time = 2

    def __init__(self, car, info, target=None):
        self.aerial = Aerial(car)

        self.aerialing = False
        super().__init__(car, info, target)
        self.arrive.allow_dodges_and_wavedashes = False
    
    def update(self):
        self.intercept = AerialIntercept(self.car, self.info.ball_predictions, self.intercept_predicate)
        self.configure(self.intercept)
        self._last_update_time = self.car.time
        if not self.intercept.is_viable:
            self.finished = True
            

    def configure(self, intercept: AerialIntercept):
        
        self.arrive.target = intercept.ground_pos
        self.aerial.target = intercept.ball.position

        self.arrive.time = intercept.time
        self.aerial.arrival_time = intercept.time

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.position[2] > 400

    def step(self, dt):
        if self.car.time > self.aerial.arrival_time:
            self.finished = True
            
        if not self.aerialing:
            super().step(dt)
            if angle_between(ground(self.car.velocity), ground_direction(self.car, self.aerial.target)) < 0.1 \
            and ground_distance(self.car, self.arrive.target) < self.aerial.target[2] * 3 + 500 \
            and norm(self.car.velocity) > self.arrive.drive.target_speed - 300:
                self.aerialing = True
                self.aerial.calculate_course()
        
        if self.aerialing:
            self.aerial.step(dt)
            self.controls = self.aerial.controls

    def render(self, draw: DrawingTool):
        super().render(draw)
        if self.aerialing:
            self.aerial.render(draw)
            draw.color(draw.cyan)
            draw.point(self.intercept.ball.position)
            draw.line(self.aerial.target, self.intercept.ball.position)