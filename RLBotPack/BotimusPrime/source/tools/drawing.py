import math
from dataclasses import dataclass

from RLUtilities.LinearAlgebra import vec3, cross
from RLUtilities.Simulation import Car, Input
from RLUtilities.GameInfo import GameInfo

from rlbot.utils.rendering.rendering_manager import RenderingManager

from utils.vector_math import loc
from utils.math import clamp


class DrawingTool:

    black = 0, 0, 0
    white = 255, 255, 255
    gray = 128, 128, 128
    blue = 0, 0, 255
    red = 255, 0, 0
    green = 0, 128, 0
    lime = 0, 255, 0
    yellow = 255, 255, 0
    orange = 225, 128, 0
    cyan = 0, 255, 255
    pink = 255, 0, 255
    purple = 128, 0, 128
    teal = 0, 128, 128

    def __init__(self, renderer: RenderingManager):
        self._renderer = renderer
        
        self._opacity = 0
        self._R = 0
        self._G = 0
        self._B = 0

        self._color = None
        self._items_drawn = 0
        self._group_id = 'default'
        self._log_text = ""


    def begin(self):
        self._opacity = 255
        self._R = 255
        self._G = 255
        self._B = 0
        self._renderer.begin_rendering(self._group_id)
        self._color = self._renderer.create_color(255, 255, 255, 0)
        self._items_drawn = 0
        self._log_text = ""

    def _check_limit(self, items=1):
        if self._items_drawn == 0:
            self.begin()
        self._items_drawn += items
        if self._items_drawn > 400:
            self._items_drawn = 0
            self._renderer.end_rendering()
            self._group_id += 'a'
            self._renderer.begin_rendering(self._group_id)
            self._color = self._renderer.create_color(
                self._opacity, self._R, self._G, self._B
            )

    def _render_logs(self):
        if not self._log_text == "":
            self._check_limit()
            self._renderer.draw_string_2d(10, 10, 1, 1, self._log_text, self._color)
            self._log_text = ""

    def execute(self):
        self._render_logs()
        if self._items_drawn > 0:
            self._renderer.end_rendering()
            self._items_drawn = 0
            self._group_id = 'default'

    def clear(self):
        self._renderer.clear_all_touched_render_groups()

    def group(self, group_id='default'):
        self.execute()
        self._group_id = group_id

    # color configuration

    def alpha(self, alpha):
        if alpha <= 1: #support both 0-1 and 0-255
            alpha *= 255
        self._color = self._renderer.create_color(int(alpha), self._R, self._G, self._B)

    def color(self, color: tuple):
        self._check_limit()
        self._R, self._G, self._B = color
        self._color = self._renderer.create_color(
            self._opacity, color[0], color[1], color[2]
        )


    # render items

    def point(self, pos: vec3, size: float = 5):
        self._check_limit()
        self._renderer.draw_rect_3d(loc(pos), size, size, 1, self._color, 1)

    def line(self, pos1: vec3, pos2: vec3):
        self._check_limit()
        self._renderer.draw_line_3d(loc(pos1), loc(pos2), self._color)

    def string(self, pos: vec3, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_3d(pos, scale, scale, str(text), self._color)

    def string2D(self, x, y, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_2d(x, y, int(scale), int(scale), str(text), self._color)



    # advanced

    def vector(self, pos: vec3, vector: vec3):
        self.line(pos, pos + vector)

    def triangle(self, pos: vec3, pointing_dir: vec3, width=50, length=50, up=vec3(0,0,1)):
        left = pos + cross(pointing_dir, up) * width / 2
        right = pos - cross(pointing_dir, up) * width / 2
        top = pos + pointing_dir * length
        self.line(left, right)
        self.line(left, top)
        self.line(right, top)


    def arc(self, pos: vec3, radius: float, start: float, end: float, segments: int = 50):
        step = (end - start) / segments
        prev_l = None

        for i in range(segments + 1):
            angle = start + step * i
            l = pos + vec3(math.cos(angle) * radius, math.sin(angle) * radius, 0)
            if prev_l is not None:
                self.line(prev_l, l)
            prev_l = l

    def circle(self, pos: vec3, radius: float):
        segments = int(clamp(radius / 20, 10, 50))
        self.arc(pos, radius, 0, math.pi * 2, segments)

    def square(self, pos: vec3, size: float):
        self.arc(pos, size / 2, 0, math.pi * 2, 4)

    def polyline(self, iterable):
        for i in range(1, len(iterable)):
            self.line(iterable[i - 1], iterable[i])

    def car_trajectory(self, car: Car, end_time: float, dt: float = 1 / 10):
        steps = []
        test_car = Car(car)
        while test_car.time < end_time:
            dt = min(dt, end_time - test_car.time)
            test_car.step(Input(), dt)
            test_car.time += dt
            steps.append(vec3(test_car.pos))
        self.polyline(steps)

    def ball_trajectory(self, ball_predictions: list, step=1, time_limit=None):
        for i in range(step, len(ball_predictions), step):
            if time_limit is not None and ball_predictions[i].t > time_limit:
                break
            self.line(ball_predictions[i - step], ball_predictions[i])

    def ball_prediction(self, info: GameInfo, time_limit=None):
        self.group('prediction')
        self.color(self.yellow)
        self.alpha(0.5)
        self.ball_trajectory(info.ball_predictions, 4, time_limit)
        self.group()

    # text logging

    def log(self, text):
        self._log_text += str(text) + "\n"

    def fps(self, dt: float):
        fps = int(1 / max(0.00000001, dt))
        if fps <= 120:
            self.log(fps)



