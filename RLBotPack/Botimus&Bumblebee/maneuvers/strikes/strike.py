import math
from typing import List, Optional

from maneuvers.driving.arrive import Arrive
from maneuvers.maneuver import Maneuver
from rlutilities.linear_algebra import vec3, dot
from rlutilities.simulation import Car, Ball
from tools.drawing import DrawingTool
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import ground_direction


class Strike(Maneuver):
    allow_backwards = False
    update_interval = 0.2
    stop_updating = 0.1
    max_additional_time = 0.4

    def __init__(self, car: Car, info: GameInfo, target: vec3 = None):
        super().__init__(car)

        self.info: GameInfo = info
        self.target: Optional[vec3] = target

        self.arrive = Arrive(car)
        self.intercept: Intercept = None

        self._has_drawn_prediction = False
        self._last_update_time = car.time
        self._should_strike_backwards = False
        self._initial_time = math.inf
        self.update_intercept()
        self._initial_time = self.intercept.time

    def intercept_predicate(self, car: Car, ball: Ball):
        return True

    def configure(self, intercept: Intercept):
        self.arrive.target = intercept.ground_pos
        self.arrive.arrival_time = intercept.time
        self.arrive.backwards = self._should_strike_backwards
        self.arrive.asap = not intercept.predicate_later_than_time

    def update_intercept(self):
        self.intercept = Intercept(self.car, self.info.ball_predictions, self.intercept_predicate)

        if self.allow_backwards:
            backwards_intercept = Intercept(self.car, self.info.ball_predictions, self.intercept_predicate,
                                            backwards=True)
            if backwards_intercept.time + 0.1 < self.intercept.time:
                self.intercept = backwards_intercept
                self._should_strike_backwards = True
            else:
                self._should_strike_backwards = False

        self.configure(self.intercept)
        self._last_update_time = self.car.time
        if not self.intercept.is_viable or self.intercept.time > self._initial_time + self.max_additional_time:
            self.finished = True

    def interruptible(self) -> bool:
        return self.arrive.interruptible()

    def step(self, dt):
        if (
            self._last_update_time + self.update_interval < self.car.time < self.intercept.time - self.stop_updating
            and self.car.on_ground and not self.controls.jump
        ):
            self.info.predict_ball(duration=self.intercept.time - self.car.time + 1)
            self._has_drawn_prediction = False
            self.update_intercept()

        if self.intercept.time - self.car.time > 1.0 and self.interruptible() and not self.car.on_ground:
            self.finished = True

        self.arrive.step(dt)
        self.controls = self.arrive.controls

        if self.arrive.drive.target_speed < 300:
            self.controls.throttle = 0

        if self.arrive.finished:
            self.finished = True

    def render(self, draw: DrawingTool):
        self.arrive.render(draw)
        draw.color(draw.lime)
        draw.circle(self.intercept.ground_pos, Ball.radius)
        draw.point(self.intercept.ball.position)

        if self.target:
            strike_direction = ground_direction(self.intercept.ground_pos, self.target)
            draw.color(draw.cyan)
            draw.triangle(self.intercept.ground_pos + strike_direction * 150, strike_direction, length=100)

        if not self._has_drawn_prediction:
            self._has_drawn_prediction = True
            draw.ball_prediction(self.info.ball_predictions, self.intercept.time)

    def pick_easiest_target(self, car: Car, ball: Ball, targets: List[vec3]) -> vec3:
        to_goal = ground_direction(ball, self.info.their_goal.center)
        return max(targets, key=lambda target: dot(ground_direction(car, ball) + to_goal * 0.5, ground_direction(ball, target)))
