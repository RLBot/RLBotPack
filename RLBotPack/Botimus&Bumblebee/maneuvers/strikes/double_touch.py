from typing import List

from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike
from rlutilities.linear_algebra import vec3
from rlutilities.mechanics import Aerial
from tools.drawing import DrawingTool
from tools.vector_math import direction, distance


class DoubleTouch(Maneuver):
    """
    Execute a regular AerialStrike, but when it finishes, look if we could continue aerialing for a second hit.
    """
    def __init__(self, aerial_strike: AerialStrike):
        super().__init__(aerial_strike.car)
        self.aerial_strike = aerial_strike
        self.info = self.aerial_strike.info

        self.aerial = Aerial(self.car)
        self.aerial.up = vec3(0, 0, -1)

        self._flight_path: List[vec3] = []

    def find_second_touch(self):
        self.info.predict_ball(duration=4.0)
        for i in range(0, len(self.info.ball_predictions), 5):
            ball = self.info.ball_predictions[i]
            if ball.position[2] < 500: break
            self.aerial.target_position = ball.position - direction(ball, self.aerial_strike.target) * 80
            self.aerial.arrival_time = ball.time
            final_car = AerialStrike.simulate_flight(self.car, self.aerial, self._flight_path)
            if distance(final_car, self.aerial.target_position) < 50:
                return

        self.finished = True

    def step(self, dt: float):
        if self.aerial_strike.finished:
            self.aerial.step(dt)
            self.controls = self.aerial.controls
            self.finished = self.aerial.finished
            if self.car.on_ground: self.finished = True

        else:
            self.aerial_strike.step(dt)
            self.controls = self.aerial_strike.controls

            if self.aerial_strike.finished:
                if not self.car.on_ground:
                    self.find_second_touch()
                else:
                    self.finished = True

    def interruptible(self) -> bool:
        return self.aerial_strike.interruptible()

    def render(self, draw: DrawingTool):
        if self.aerial_strike.finished:
            draw.color(draw.pink)
            draw.crosshair(self.aerial.target_position)
            draw.color(draw.lime)
            draw.polyline(self._flight_path)
        else:
            self.aerial_strike.render(draw)
