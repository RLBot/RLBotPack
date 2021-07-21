import math

from utility import draw
from utility.curves import curve_from_arrival_dir
from utility.info import Field
from utility.rlmath import fix_ang, clip
from utility.vec import Vec3, normalize, angle_between, xy


class AimCone:
    def __init__(self, right_most, left_most):
        # Right angle and direction
        self.right_ang = math.atan2(right_most.y, right_most.x)
        self.right_dir = normalize(right_most)
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

            draw.line(car_pos, goto, draw.color(150, 150, 150))
            draw.line(point, goto, draw.color(150, 150, 150))
            draw.bezier([car_pos, goto, point], draw.grey())

            return goto, 0.5
        else:
            return None, 1

    def draw(self, center, arm_len=500, r=255, g=255, b=255):
        draw.fan(center, self.right_ang, self.span_size(), arm_len, draw.color(r, g, b))
