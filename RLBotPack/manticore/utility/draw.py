import math
from sys import modules
from typing import Optional, List

from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.rendering.rendering_manager import RenderingManager, DummyRenderer

import utility.curves as curves
from utility import vec
from utility.vec import Vec3, normalize, axis_to_rotation, dot


def renderer() -> RenderingManager:
    try:
        return renderer.__renderer__
    except AttributeError:
        renderer.__renderer__ = DummyRenderer
    return renderer.__renderer__


def color(r: int, g: int, b: int, a: int = 255):
    return default().renderer.create_color(a, r, g, b)


def colorf(r: float, g: float, b: float, a: float = 1.0):
    return color(int(r * 255), int(g * 255), int(b * 255), int(a * 255))


def black():
    return default().renderer.black()


def white():
    return default().renderer.white()


def grey():
    return default().renderer.gray()


def blue():
    return color(130, 170, 255)


def red():
    return default().renderer.red()


def green():
    return default().renderer.green()


def lime():
    return default().renderer.lime()


def yellow():
    return default().renderer.yellow()


def orange():
    return color(235, 155, 30)


def cyan():
    return default().renderer.cyan()


def pink():
    return default().renderer.pink()


def purple():
    return default().renderer.purple()


def teal():
    return default().renderer.teal()


def team_color(team: Optional[int] = None):
    team = team or default().renderer.bot_team
    return blue() if team == 0 else orange()


def team_color_sec(team: Optional[int] = None):
    team = team or default().renderer.bot_team
    return cyan() if team == 0 else red()


def team_color_ter(team: Optional[int] = None):
    team = team or default().renderer.bot_team
    return cyan() if team == 0 else red()


class DebugDrawer:
    def __init__(self, renderer):
        self.renderer = renderer

    def rect_2d(self, x: int, y: int, width: int, height: int, fill: bool, color):
        self.renderer.draw_rect_2d(x, y, width, height, fill, color)

    def string_2d(self, x: int, y: int, scale: int, text: str, color):
        self.renderer.draw_string_2d(x, y, scale, scale, text, color)

    def rect_3d(self, pos: Vec3, width: float, height: float, color, fill: bool = True, centered: bool = True):
        self.renderer.draw_rect_3d(pos, width, height, fill, color, centered)

    def string_3d(self, pos: Vec3, scale: int, text: str, color):
        self.renderer.draw_string_3d(pos, scale, scale, text, color)

    def line(self, start: Vec3, end: Vec3, color):
        self.renderer.draw_line_3d(start, end, color)

    def polyline(self, posses: List[Vec3], color):
        self.renderer.draw_polyline_3d(posses, color)

    def circle(self, center: Vec3, normal: Vec3, radius: float, color):
        # Construct the arm that will be rotated
        pieces = int(radius ** 0.7) + 5
        arm = normalize(vec.cross(normal, center)) * radius
        angle = 2 * math.pi / pieces
        rotation_mat = axis_to_rotation(angle * normalize(normal))
        points = [center + arm]

        for i in range(pieces):
            arm = dot(rotation_mat, arm)
            points.append(center + arm)

        self.renderer.draw_polyline_3d(points, color)

    def cross(self, point: Vec3, color, arm_length: float = 30):
        self.line(point + Vec3(x=arm_length), point + Vec3(x=-arm_length), color)
        self.line(point + Vec3(y=arm_length), point + Vec3(y=-arm_length), color)
        self.line(point + Vec3(z=arm_length), point + Vec3(z=-arm_length), color)

    def cross2(self, point: Vec3, color, arm_length: float = 30):
        r = arm_length / 1.4142135
        self.line(point + Vec3(r, r, r), point + Vec3(-r, -r, -r), color)
        self.line(point + Vec3(r, r, -r), point + Vec3(-r, -r, r), color)
        self.line(point + Vec3(r, -r, -r), point + Vec3(-r, r, r), color)
        self.line(point + Vec3(r, -r, r), point + Vec3(-r, r, -r), color)

    def cube(self, center: Vec3, size: float, color):
        r = size / 2.0

        self.line(center + Vec3(-r, -r, -r), center + Vec3(-r, -r, r), color)
        self.line(center + Vec3(r, -r, -r), center + Vec3(r, -r, r), color)
        self.line(center + Vec3(-r, r, -r), center + Vec3(-r, r, r), color)
        self.line(center + Vec3(r, r, -r), center + Vec3(r, r, r), color)

        self.line(center + Vec3(-r, -r, -r), center + Vec3(-r, r, -r), color)
        self.line(center + Vec3(r, -r, -r), center + Vec3(r, r, -r), color)
        self.line(center + Vec3(-r, -r, r), center + Vec3(-r, r, r), color)
        self.line(center + Vec3(r, -r, r), center + Vec3(r, r, r), color)

        self.line(center + Vec3(-r, -r, -r), center + Vec3(r, -r, -r), color)
        self.line(center + Vec3(-r, -r, r), center + Vec3(r, -r, r), color)
        self.line(center + Vec3(-r, r, -r), center + Vec3(r, r, -r), color)
        self.line(center + Vec3(-r, r, r), center + Vec3(r, r, r), color)

    def octahedron(self, center: Vec3, size: float, color):
        r = size / 2.0

        self.line(center + Vec3(r, 0, 0), center + Vec3(0, r, 0), color)
        self.line(center + Vec3(0, r, 0), center + Vec3(-r, 0, 0), color)
        self.line(center + Vec3(-r, 0, 0), center + Vec3(0, -r, 0), color)
        self.line(center + Vec3(0, -r, 0), center + Vec3(r, 0, 0), color)

        self.line(center + Vec3(r, 0, 0), center + Vec3(0, 0, r), color)
        self.line(center + Vec3(0, 0, r), center + Vec3(-r, 0, 0), color)
        self.line(center + Vec3(-r, 0, 0), center + Vec3(0, 0, -r), color)
        self.line(center + Vec3(0, 0, -r), center + Vec3(r, 0, 0), color)

        self.line(center + Vec3(0, r, 0), center + Vec3(0, 0, r), color)
        self.line(center + Vec3(0, 0, r), center + Vec3(0, -r, 0), color)
        self.line(center + Vec3(0, -r, 0), center + Vec3(0, 0, -r), color)
        self.line(center + Vec3(0, 0, -r), center + Vec3(0, r, 0), color)

    def bezier(self, points: List[Vec3], color, time_step: float=0.0625):
        time = 0
        last_point = points[0]
        while time < 1:
            time += time_step
            current_point = curves.bezier(time, points)
            self.renderer.draw_line_3d(last_point, current_point, color)
            last_point = current_point

    def fan(self, center: Vec3, right_ang: float, radians: float, radius: float, color):
        steps = int((radius ** 0.7) * radians / math.tau) + 5
        step_size = radians / (steps - 1)

        points = [center]

        for i in range(steps):
            ang = right_ang - step_size * i
            arm_dir = Vec3(math.cos(ang), math.sin(ang), 0)
            end = center + arm_dir * radius
            points.append(end)

        points.append(center)

        self.polyline(points, color)


def ball_path(bot: BaseAgent, color, duration: float = 4.0, step_size: int = 10):
    ball_prediction = bot.get_ball_prediction_struct()
    if ball_prediction is not None and duration > 0 and step_size > 0:
        time_passed = 0
        steps_taken = 0
        locations = [ball_prediction.slices[0].physics.location]
        while time_passed < duration and steps_taken + step_size < ball_prediction.num_slices:
            steps_taken += step_size
            time_passed += step_size * 0.016666
            locations.append(ball_prediction.slices[steps_taken].physics.location)

        if steps_taken > 0:
            renderer().draw_polyline_3d(locations, color)


def default() -> DebugDrawer:
    return default.__drawer__


def setup(renderer):
    renderer.__renderer__ = renderer

    # Bind module methods to global renderer.
    default.__drawer__ = DebugDrawer(renderer)
    module = modules[__name__]
    for method_name in dir(default.__drawer__):
        if not callable(getattr(default.__drawer__, method_name)):
            continue
        if method_name.startswith("_"):
            continue
        setattr(module, method_name, default.__drawer__.__getattribute__(method_name))


def rect_2d(x: int, y: int, width: int, height: int, fill: bool, color):
    pass


def string_2d(x: int, y: int, scale: int, text: str, color):
    pass


def rect_3d(pos: Vec3, width: float, height: float, color, fill: bool = True, centered: bool = True):
    pass


def string_3d(pos: Vec3, scale: int, text: str, color):
    pass


def line(start: Vec3, end: Vec3, color):
    pass


def polyline(posses: List[Vec3], color):
    pass


def circle(center: Vec3, normal: Vec3, radius: float, color):
    pass


def cross(point: Vec3, color, arm_length: float = 30):
    pass


def cross2(point: Vec3, color, arm_length: float = 30):
    pass


def cube(center: Vec3, size: float, color):
    pass


def octahedron(center: Vec3, size: float, color):
    pass


def bezier(points: List[Vec3], color, time_step: float=0.05):
    pass


def fan(center: Vec3, right_ang: float, radians: float, radius: float, color):
    pass
