from maneuvers.kit import *

from maneuvers.strikes.strike import Strike
from maneuvers.driving.arrive import Arrive
from maneuvers.air.aerial import Aerial

class AerialStrike(Strike):

    stop_updating = 1.5
    max_additional_time = 2

    def __init__(self, car, info, target=None):
        self.aerial = Aerial(car, vec3(0,0,0), 99999)
        self.aerial.aerial_turn = AerialTurn(car, car.theta)
        self.final_turn = AerialTurn(car, car.theta)

        self.aerialing = False
        super().__init__(car, info, target)
    
    def update(self):
        self.intercept = AerialIntercept(self.car, self.info.ball_predictions, self.intercept_predicate, 1000)
        self.configure(self.intercept)
        self._last_update_time = self.car.time
        if not self.intercept.is_viable:
            self.finished = True
            

    def configure(self, intercept: AerialIntercept):
        
        self.arrive.target = intercept.ground_pos
        self.aerial.target = intercept.ball.pos

        self.arrive.time = intercept.time
        self.aerial.t_arrival = intercept.time

    def intercept_predicate(self, car: Car, ball: Ball):
        return ball.pos[2] > 400

    def step(self, dt):
        if self.car.time > self.aerial.t_arrival:
            self.finished = True
            
        if not self.aerialing:
            super().step(dt)
            if angle_to(self.car, self.arrive.target) < 0.2 \
            and ground_distance(self.car, self.arrive.target) < self.aerial.target[2] * 3 + 500 \
            and norm(self.car.vel) > self.arrive.drive.target_speed - 300:
                self.aerialing = True
                self.aerial.calculate_course()
        
        if self.aerialing:
            if norm(self.aerial.A) > 100 or self.car.on_ground:
                self.aerial.step(dt)
                self.controls = self.aerial.controls
            else:
                self.final_turn.target = look_at(direction(self.aerial.target, self.intercept.ball))
                self.final_turn.step(dt)
                self.controls = self.final_turn.controls

    def render(self, draw: DrawingTool):
        super().render(draw)
        if self.aerialing:
            self.aerial.render(draw)
            draw.color(draw.cyan)
            draw.point(self.intercept.ball.pos)
            draw.line(self.aerial.target, self.intercept.ball.pos)