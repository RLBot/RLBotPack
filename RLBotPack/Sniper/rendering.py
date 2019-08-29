import math

from rlmath import axis_to_rotation
from vec import Vec3, cross, normalize, dot


def draw_circle(bot, center: Vec3, normal: Vec3, radius: float, pieces: int, color_func):
    # Construct the arm that will be rotated
    arm = normalize(cross(normal, center)) * radius
    angle = 2 * math.pi / pieces
    rotation_mat = axis_to_rotation(angle * normalize(normal))
    points = [center + arm]

    for i in range(pieces):
        arm = dot(rotation_mat, arm)
        points.append(center + arm)

    bot.renderer.draw_polyline_3d(points, color_func())
