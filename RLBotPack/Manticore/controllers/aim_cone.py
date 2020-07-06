import math

from util import rendering
from util.curves import curve_from_arrival_dir
from util.info import Field
from util.rlmath import fix_ang, clip
from util.vec import Vec3, normalize, angle_between, xy


class AimCone:
    def __init__(self, right_most, left_most):
        # Right angle and direction
        if isinstance(right_most, float):
            self.right_ang = fix_ang(right_most)
            self.right_dir = Vec3(math.cos(right_most), math.sin(right_most), 0)
        elif isinstance(right_most, Vec3):
            self.right_ang = math.atan2(right_most.y, right_most.x)
            self.right_dir = normalize(right_most)
        # Left angle and direction
        if isinstance(left_most, float):
            self.left_ang = fix_ang(left_most)
            self.left_dir = Vec3(math.cos(left_most), math.sin(left_most), 0)
        elif isinstance(left_most, Vec3):
            self.left_ang = math.atan2(left_most.y, left_most.x)
            self.left_dir = normalize(left_most)

    def contains_direction(self, direction, span_offset: float=0):
        ang_delta = angle_between(direction, self.get_center_dir())
        return abs(ang_delta) < self.span_size() / 2.0 + span_offset

    def span_size(self):
        if self.right_ang < self.left_ang:
            return math.tau + self.right_ang - self.left_ang
        else:
            return self.right_ang - self.left_ang

    def get_center_ang(self):
        return fix_ang(self.right_ang - self.span_size() / 2)

    def get_center_dir(self):
        ang = self.get_center_ang()
        return Vec3(math.cos(ang), math.sin(ang), 0)

    def get_closest_dir_in_cone(self, direction, span_offset: float=0):
        if self.contains_direction(direction, span_offset):
            return normalize(direction)
        else:
            ang_to_right = abs(angle_between(direction, self.right_dir))
            ang_to_left = abs(angle_between(direction, self.left_dir))
            return self.right_dir if ang_to_right < ang_to_left else self.left_dir

    def get_goto_point(self, bot, src, point):
        point = xy(point)
        desired_dir = self.get_center_dir()

        desired_dir_inv = -1 * desired_dir
        car_pos = xy(src)
        point_to_car = car_pos - point

        ang_to_desired_dir = angle_between(desired_dir_inv, point_to_car)

        ANG_ROUTE_ACCEPTED = math.pi / 4.3
        can_go_straight = abs(ang_to_desired_dir) < self.span_size() / 2.0
        can_with_route = abs(ang_to_desired_dir) < self.span_size() / 2.0 + ANG_ROUTE_ACCEPTED
        point = point + desired_dir_inv * 50
        if can_go_straight:
            return point, 1.0
        elif can_with_route:
            ang_to_right = abs(angle_between(point_to_car, -1 * self.right_dir))
            ang_to_left = abs(angle_between(point_to_car, -1 * self.left_dir))
            closest_dir = self.right_dir if ang_to_right < ang_to_left else self.left_dir

            goto = curve_from_arrival_dir(car_pos, point, closest_dir)

            goto.x = clip(goto.x, -Field.WIDTH / 2, Field.WIDTH / 2)
            goto.y = clip(goto.y, -Field.LENGTH / 2, Field.LENGTH / 2)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car_pos, goto, bot.renderer.create_color(255, 150, 150, 150))
                bot.renderer.draw_line_3d(point, goto, bot.renderer.create_color(255, 150, 150, 150))

                # Bezier
                rendering.draw_bezier(bot, [car_pos, goto, point])

            return goto, 0.5
        else:
            return None, 1

    def draw(self, bot, center, arm_len=500, arm_count=5, r=255, g=255, b=255):
        renderer = bot.renderer
        ang_step = self.span_size() / (arm_count - 1)

        for i in range(arm_count):
            ang = self.right_ang - ang_step * i
            arm_dir = Vec3(math.cos(ang), math.sin(ang), 0)
            end = center + arm_dir * arm_len
            alpha = 255 if i == 0 or i == arm_count - 1 else 110
            renderer.draw_line_3d(center, end, renderer.create_color(alpha, r, g, b))
