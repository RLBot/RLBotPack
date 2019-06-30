from maneuvers.kit import *

from maneuvers.driving.arrive import Arrive

class Strike(Maneuver):

    allow_backwards = False
    update_interval = 0.3
    stop_updating = 0.8
    max_additional_time = 1

    def __init__(self, car: Car, info: GameInfo, target: vec3 = None):
        super().__init__(car)
        
        self.info = info
        self.target = target

        self.arrive = Arrive(car)
        self.intercept: Intercept = None

        self._has_drawn_prediction = False
        self._last_update_time = car.time
        self._should_strike_backwards = False
        self._initial_time = 999999
        self.update()
        self._initial_time = self.intercept.time

    def intercept_predicate(self, car: Car, ball: Ball):
        return True

    def configure(self, intercept: Intercept):
        self.arrive.target = intercept.ground_pos
        self.arrive.time = intercept.time
        self.arrive.drive.backwards = self._should_strike_backwards

    def update(self):
        self.intercept = Intercept(self.car, self.info.ball_predictions, self.intercept_predicate)
        if self.allow_backwards:
            backwards_intercept = Intercept(self.car, self.info.ball_predictions, self.intercept_predicate, backwards=True)
            if backwards_intercept.time + 0.1 < self.intercept.time:
                self.intercept = backwards_intercept
                self._should_strike_backwards = True
            else:
                self._should_strike_backwards = False

        self.configure(self.intercept)
        self._last_update_time = self.car.time
        if not self.intercept.is_viable or self.intercept.time > self._initial_time + self.max_additional_time:
            self.finished = True
            

    def update_requirement(self):
        return self.intercept.time > self.car.time + self.stop_updating

    def step(self, dt):
        self.arrive.step(dt)
        self.controls = self.arrive.controls
        self.finished = self.arrive.finished

        if self.arrive.drive.target_speed < 300:
            self.controls.throttle = 0

        if self.car.time > self._last_update_time + self.update_interval:

            if self.update_requirement():

                prediction_steps = int((self.intercept.time - self.car.time + 1) * 60)
                self.info.predict_ball(prediction_steps, 1/60)
                self._has_drawn_prediction = False
                self.update()

    def render(self, draw: DrawingTool):
        self.arrive.render(draw)
        draw.color(draw.lime)
        draw.circle(self.intercept.ground_pos, 93)
        draw.point(self.intercept.ball.pos)

        if self.target is not None:
            draw.color(draw.yellow)
            draw.point(self.target)

        if not self._has_drawn_prediction:
            self._has_drawn_prediction = True
            draw.ball_prediction(self.info, self.intercept.time)


    @staticmethod
    def pick_easiest_target(car: Car, ball: Ball, targets) -> vec3:
        best_dot = -99
        best_target = None
        for target in targets:
            this_dot = dot(ground_direction(car, ball), ground_direction(ball, target))
            if this_dot > best_dot:
                best_dot = this_dot
                best_target = target
        return best_target

    @staticmethod
    def pick_easiest_direction(car: Car, ball: Ball, directions) -> vec3:
        best_dot = -99
        best_direction = None
        for d in directions:
            this_dot = dot(ground_direction(car, ball), d)
            if this_dot > best_dot:
                best_dot = this_dot
                best_direction = d
        return best_direction
