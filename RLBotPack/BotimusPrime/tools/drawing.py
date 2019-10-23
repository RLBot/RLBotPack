import math
from dataclasses import dataclass
from typing import List

from rlutilities.linear_algebra import vec3, cross
from rlutilities.simulation import Car, Input, Ball

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

        self._items_drawn = 0
        self._group_id = 'default'
        self._log_text = ""


    def begin(self):
        self._renderer.begin_rendering(self._group_id)
        self._items_drawn = 0
        self._log_text = ""

    def _check_limit(self, items=1):
        if self._items_drawn == 0:
            self.begin()
        if self._items_drawn > 400:
            self._items_drawn = 0
            self._renderer.end_rendering()
            self._group_id += 'a'
            self._renderer.begin_rendering(self._group_id)
        self._items_drawn += items

    def _render_logs(self):
        if not self._log_text == "":
            self._check_limit()
            self._renderer.draw_string_2d(10, 10, 1, 1, self._log_text, self.__getcolor())
            self._log_text = ""

    def execute(self):
        self._render_logs()
        if self._items_drawn > 0:
            self._renderer.end_rendering()
            self._items_drawn = 0
            self._group_id = 'default'

    def clear(self):
        self._renderer.clear_all_touched_render_groups()
        self.begin()

    def group(self, group_id='default'):
        self.execute()
        self._group_id = group_id

    # color configuration

    def color(self, color: tuple):
        self._R, self._G, self._B = color

    def __getcolor(self):
        if not self._renderer.is_rendering():
            self.begin()
        return self._renderer.create_color(
            self._opacity, self._R, self._G, self._B
        )

    # render items

    def point(self, pos: vec3, size: float = 5):
        self._check_limit()
        self._renderer.draw_rect_3d(loc(pos) + vec3(0,0,5), size, size, 1, self.__getcolor(), 1)

    def line(self, pos1: vec3, pos2: vec3):
        self._check_limit()
        p1, p2 = vec3(loc(pos1)), vec3(loc(pos2))
        if p1[2] < 10: p1[2] = 10
        if p2[2] < 10: p2[2] = 10
        self._renderer.draw_line_3d(p1, p2, self.__getcolor())

    def string(self, pos: vec3, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_3d(pos, scale, scale, str(text), self.__getcolor())

    def string2D(self, x, y, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_2d(x, y, int(scale), int(scale), str(text), self.__getcolor())

    def polyline(self, iterable):
        if len(iterable) > 1:
            self._check_limit()
            self._renderer.draw_polyline_3d(iterable, self.__getcolor())


    # advanced
    def cyclic_polyline(self, points: List[vec3]):
        points.append(points[0])
        self.polyline(points)
        points.pop()

    def vector(self, pos: vec3, vector: vec3):
        self.line(pos, pos + vector)

    def crosshair(self, pos: vec3, size: int = 50):
        self.line(pos + vec3(size, 0, 0), pos - vec3(size, 0, 0))
        self.line(pos + vec3(0, size, 0), pos - vec3(0, size, 0))
        self.line(pos + vec3(0, 0, size), pos - vec3(0, 0, size))

    def triangle(self, pos: vec3, pointing_dir: vec3, width=50, length=50, up=vec3(0,0,1)):
        left = pos + cross(pointing_dir, up) * width / 2
        right = pos - cross(pointing_dir, up) * width / 2
        top = pos + pointing_dir * length
        self.cyclic_polyline([left, right, top])


    def arc(self, pos: vec3, radius: float, start: float, end: float, segments: int = 50):
        step = (end - start) / segments
        points = []

        for i in range(segments):
            angle = start + step * i
            points.append(pos + vec3(math.cos(angle) * radius, math.sin(angle) * radius, 0))
        
        self.cyclic_polyline(points)

    def circle(self, pos: vec3, radius: float):
        segments = int(clamp(radius / 20, 10, 50))
        self.arc(pos, radius, 0, math.pi * 2, segments)

    def square(self, pos: vec3, size: float):
        self.arc(pos, size / 2, 0, math.pi * 2, 4)


    def car_trajectory(self, car: Car, end_time: float, dt: float = 1 / 10):
        steps = []
        test_car = Car(car)
        while test_car.time < end_time:
            dt = min(dt, end_time - test_car.time)
            test_car.step(Input(), dt)
            test_car.time += dt
            steps.append(vec3(test_car.position))
        self.polyline(steps)

    def ball_trajectory(self, ball_predictions: List[Ball], step=1, time_limit=None):
        points = []
        for i in range(step, len(ball_predictions), step):
            if time_limit is not None and ball_predictions[i].time > time_limit:
                break
            points.append(ball_predictions[i].position)
        self.polyline(points)

    def ball_prediction(self, info, time_limit=None):
        self.group('prediction')
        self.color(self.yellow)
        self.ball_trajectory(info.ball_predictions, 4, time_limit)
        self.group()

    # text logging

    def log(self, text):
        self._log_text += str(text) + "\n"

    def fps(self, dt: float):
        fps = int(1 / max(0.00000001, dt))
        if fps <= 120:
            self.log(fps)



