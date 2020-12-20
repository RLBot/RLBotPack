from typing import List

from utility.rlmath import clip
from utility.vec import normalize, Vec3


def curve_from_arrival_dir(src: Vec3, target: Vec3, arrival_direction: Vec3, w=1):
    """
    Returns a point that is equally far from src and target on the line going through target with the given direction
    """
    dir = normalize(arrival_direction)
    tx = target.x
    ty = target.y
    sx = src.x
    sy = src.y
    dx = dir.x
    dy = dir.y

    t = - (tx * tx - 2 * tx * sx + ty * ty - 2 * ty * sy + sx * sx + sy * sy) / (2 * (tx * dx + ty * dy - sx * dx - sy * dy))
    t = clip(t, -1700, 1700)

    return target + w * t * dir


def bezier(t: float, points: List[Vec3]) -> Vec3:
    """
    Returns a point on a bezier curve made from the given controls points
    """
    n = len(points)
    if n == 1:
        return points[0]
    else:
        return (1 - t) * bezier(t, points[0:-1]) + t * bezier(t, points[1:n])
