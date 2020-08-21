from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike
from rlutilities.linear_algebra import vec3
from rlutilities.mechanics import Aerial
from tools.intercept import AirToAirIntercept
from tools.drawing import DrawingTool
from tools.vector_math import direction


class DoubleTouch(Maneuver):
    """
    Execute a regular AerialStrike, but when it finishes, look if we could continue aerialing for a second hit.
    """
    def __init__(self, aerial_strike: AerialStrike):
        super().__init__(aerial_strike.car)
        self.aerial_strike = aerial_strike
        self.info = self.aerial_strike.info

        self.aerial = Aerial(self.car)

    def find_second_touch(self):
        self.info.predict_ball(time_limit=3.0)
        intercept = AirToAirIntercept(self.car, self.info.ball_predictions)
        self.aerial.target = intercept.position - direction(intercept, self.aerial_strike.target) * 80
        self.aerial.up = vec3(0, 0, -1)
        self.aerial.arrival_time = intercept.time

        if not intercept.is_viable:
            self.finished = True

    def step(self, dt: float):
        if self.aerial_strike.finished:
            self.aerial.step(dt)
            self.controls = self.aerial.controls
            self.finished = self.aerial.finished
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
            draw.crosshair(self.aerial.target)
        else:
            self.aerial_strike.render(draw)
