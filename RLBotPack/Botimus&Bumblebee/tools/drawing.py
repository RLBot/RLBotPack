import math
from typing import List

from rlbot.utils.rendering.rendering_manager import RenderingManager

from rlutilities.linear_algebra import vec3, cross
from rlutilities.simulation import Ball
from tools.math import clamp
from tools.vector_math import to_vec3


class DrawingTool:
    black = 0, 0, 0
    white = 255, 255, 255
    gray = 128, 128, 128
    blue = 0, 0, 255
    red = 255, 70, 70
    green = 0, 128, 0
    lime = 0, 255, 0
    yellow = 255, 255, 0
    orange = 225, 128, 0
    cyan = 0, 255, 255
    pink = 255, 0, 255
    purple = 128, 0, 128
    teal = 0, 128, 128

    def __init__(self, renderer: RenderingManager, team: int):
        self._renderer = renderer
        self._team = str(team)

        self._opacity = 255
        self._R = 0
        self._G = 0
        self._B = 0

        self._items_drawn = 0
        self._group_id = 'default'

    def begin(self):
        self._renderer.begin_rendering(self._group_id + self._team)
        self._items_drawn = 0

    def _check_limit(self, items=1):
        if self._items_drawn == 0:
            self.begin()
        if self._items_drawn > 400:
            self._items_drawn = 0
            self._renderer.end_rendering()
            self._group_id += 'a'
            self._renderer.begin_rendering(self._group_id + self._team)
        self._items_drawn += items

    def execute(self):
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

    def _get_color(self):
        if not self._renderer.is_rendering():
            self.begin()
        return self._renderer.create_color(
            self._opacity, self._R, self._G, self._B
        )

    @staticmethod
    def visible(pos: vec3) -> vec3:
        # make sure the position isn't below the floor or hidden in the grass
        if pos[2] < 10:
            return vec3(pos[0], pos[1], 10)
        return pos

    # primitive render items

    def point(self, pos: vec3, size: float = 5):
        self._check_limit()
        self._renderer.draw_rect_3d(self.visible(to_vec3(pos)), size, size, 1, self._get_color(), 1)

    def line(self, pos1: vec3, pos2: vec3):
        self._check_limit()
        p1, p2 = (self.visible(to_vec3(pos)) for pos in [pos1, pos2])
        self._renderer.draw_line_3d(p1, p2, self._get_color())

    def string(self, pos: vec3, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_3d(pos, scale, scale, str(text), self._get_color())

    def screen_string(self, x, y, text, scale=1):
        self._check_limit()
        self._renderer.draw_string_2d(x, y, int(scale), int(scale), str(text), self._get_color())

    def polyline(self, points: List[vec3]):
        if len(points) > 1:
            self._check_limit(len(points))
            self._renderer.draw_polyline_3d([self.visible(p) for p in points], self._get_color())

    # advanced shapes

    def closed_polyline(self, points: List[vec3]):
        self.polyline(points + [points[0]])

    def vector(self, pos: vec3, vector: vec3):
        self.line(pos, pos + vector)

    def crosshair(self, pos: vec3, size: int = 50):
        self.line(pos + vec3(size, 0, 0), pos - vec3(size, 0, 0))
        self.line(pos + vec3(0, size, 0), pos - vec3(0, size, 0))
        self.line(pos + vec3(0, 0, size), pos - vec3(0, 0, size))

    def triangle(self, pos: vec3, pointing_dir: vec3, width=50, length=50, up=vec3(0, 0, 1)):
        left = pos + cross(pointing_dir, up) * width / 2
        right = pos - cross(pointing_dir, up) * width / 2
        top = pos + pointing_dir * length
        self.closed_polyline([left, right, top])

    def arc(self, pos: vec3, radius: float, start_angle: float, end_angle: float):
        segments = int(clamp(radius * abs(start_angle - end_angle) / 20, 10, 50))
        step = (end_angle - start_angle) / segments
        points = []

        for i in range(segments + 1):
            angle = start_angle + step * i
            points.append(pos + vec3(math.cos(angle) * radius, math.sin(angle) * radius, 0))

        self.polyline(points)

    def circle(self, pos: vec3, radius: float):
        segments = int(clamp(radius / 20, 10, 50))
        step = 2 * math.pi / segments
        points = []

        for i in range(segments):
            angle = step * i
            points.append(pos + vec3(math.cos(angle), math.sin(angle), 0) * radius)

        self.closed_polyline(points)

    def square(self, pos: vec3, size: float):
        self.closed_polyline([
            pos + vec3(-size/2, -size/2, 0),
            pos + vec3(size/2, -size/2, 0),
            pos + vec3(size/2, size/2, 0),
            pos + vec3(-size/2, size/2, 0),
        ])

    def ball_prediction(self, ball_predictions: List[Ball], time_limit: float = None):
        points = [ball.position for ball in ball_predictions if not time_limit or ball.time < time_limit]
        self.group('prediction')
        self.color(self.yellow)
        self.polyline(points)
        self.group()
