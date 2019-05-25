import math

from RLUtilities.LinearAlgebra import *


FIELD_WIDTH = 8192
FIELD_LENGTH = 10240
FILED_HEIGHT = 2044
GOAL_WIDTH = 1900
GOAL_HEIGHT = 640
GRAVITY = vec3(0, 0, -650)
BALL_RADIUS = 92


X = 0
Y = 1
Z = 2


class Zone2d:
    def __init__(self, cornerA, cornerB):
        self.cornerMin = vec3(min(cornerA[X], cornerB[X]), min(cornerA[Y], cornerB[Y]), 0)
        self.cornerMax = vec3(max(cornerA[X], cornerB[X]), max(cornerA[Y], cornerB[Y]), 0)

    def contains(self, point):
        return self.cornerMin[X] <= point[X] <= self.cornerMax[X]\
               and self.cornerMin[Y] <= point[Y] <= self.cornerMax[Y]


class Zone3d:
    def __init__(self, cornerA, cornerB):
        self.cornerMin = vec3(min(cornerA[X], cornerB[X]), min(cornerA[Y], cornerB[Y]), min(cornerA[Z], cornerB[Z]))
        self.cornerMax = vec3(max(cornerA[X], cornerB[X]), max(cornerA[Y], cornerB[Y]), max(cornerA[Z], cornerB[Z]))

    def contains(self, point):
        return self.cornerMin[X] <= point[X] <= self.cornerMax[X]\
               and self.cornerMin[Y] <= point[Y] <= self.cornerMax[Y]\
               and self.cornerMin[Z] <= point[Z] <= self.cornerMax[Z]


# returns sign of x, and 0 if x == 0
def sign0(x) -> float:
    return x and (1, -1)[x < 0]


def sign(x) -> float:
    return (1, -1)[x < 0]


def clip01(x) -> float:
    return clip(x, 0, 1)


def lerp(a, b, t: float):
    return (1 - t) * a + t * b


def inv_lerp(a, b, v) -> float:
    return a if b - a == 0 else (v - a) / (b - a)


def remap(prev_low, prev_high, new_low, new_high, v) -> float:
    out = inv_lerp(prev_low, prev_high, v)
    out = lerp(new_low, new_high, out)
    return out


def fix_ang(ang: float) -> float:
    """
    Transforms the given angle into the range -pi...pi
    """
    return ((ang + math.pi) % math.tau) - math.pi


def proj_onto(src: vec3, dir: vec3) -> vec3:
    """
    Returns the vector component of src that is parallel with dir, i.e. the projection of src onto dir.
    """
    try:
        return (dot(src, dir) / dot(dir, dir)) * dir
    except ZeroDivisionError:
        return vec3()


def proj_onto_size(src: vec3, dir: vec3) -> float:
    """
    Returns the size of the vector that is the project of src onto dir
    """
    try:
        dir_n = normalize(dir)
        return dot(src, dir_n) / dot(dir_n, dir_n)  # can be negative!
    except ZeroDivisionError:
        return norm(src)


def rotated_2d(vec: vec3, ang: float) -> vec3:
    c = math.cos(ang)
    s = math.sin(ang)
    return vec3(c * vec[X] - s * vec[Y],
                s * vec[X] + c * vec[Y])


def is_near_wall(point: vec3, offset: float=130) -> bool:
    return abs(point[X]) > FIELD_WIDTH - offset or abs(point[Y]) > FIELD_LENGTH - offset  # TODO Add diagonal walls


def curve_from_arrival_dir(src, target, arrival_direction, w=1):
    """
    Returns a point that is equally far from src and target on the line going through target with the given direction
    """
    dir = normalize(arrival_direction)
    tx = target[X]
    ty = target[Y]
    sx = src[X]
    sy = src[Y]
    dx = dir[X]
    dy = dir[Y]

    t = - (tx * tx - 2 * tx * sx + ty * ty - 2 * ty * sy + sx * sx + sy * sy) / (2 * (tx * dx + ty * dy - sx * dx - sy * dy))
    t = clip(t, -1700, 1700)

    return target + w * t * dir


def bezier(t: float, points: list) -> vec3:
    """
    Returns a point on a bezier curve made from the given controls points
    """
    n = len(points)
    if n == 1:
        return points[0]
    else:
        return (1 - t) * bezier(t, points[0:-1]) + t * bezier(t, points[1:n])


def is_closer_to_goal_than(a: vec3, b: vec3, team_index):
    """ Returns true if a is closer than b to goal owned by the given team """
    return (a[Y] < b[Y], a[Y] > b[Y])[team_index]
