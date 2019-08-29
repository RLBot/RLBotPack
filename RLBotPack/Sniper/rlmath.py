from vec import *


class Zone2d:
    def __init__(self, cornerA, cornerB):
        self.cornerMin = Vec3(min(cornerA.x, cornerB.x), min(cornerA.y, cornerB.y), 0)
        self.cornerMax = Vec3(max(cornerA.x, cornerB.x), max(cornerA.y, cornerB.y), 0)

    def contains(self, point):
        return self.cornerMin.x <= point.x <= self.cornerMax.x\
               and self.cornerMin.y <= point.y <= self.cornerMax.y


class Zone3d:
    def __init__(self, cornerA, cornerB):
        self.cornerMin = Vec3(min(cornerA.x, cornerB.x), min(cornerA.y, cornerB.y), min(cornerA.z, cornerB.z))
        self.cornerMax = Vec3(max(cornerA.x, cornerB.x), max(cornerA.y, cornerB.y), max(cornerA.z, cornerB.z))

    def contains(self, point):
        return self.cornerMin.x <= point.x <= self.cornerMax.x\
               and self.cornerMin.y <= point.y <= self.cornerMax.y\
               and self.cornerMin.z <= point.z <= self.cornerMax.z


# returns sign of x, and 0 if x == 0
def sign0(x) -> float:
    return x and (1, -1)[x < 0]


def sign(x) -> float:
    return (1, -1)[x < 0]


def clip(x, minimum, maximum):
    return min(max(minimum, x), maximum)


def clip01(x) -> float:
    return clip(x, 0, 1)


def angle_between(v: Vec3, u: Vec3) -> float:
    return math.acos(dot(normalize(v), normalize(u)))


def axis_to_rotation(axis: Vec3) -> Mat33:
    radians = norm(axis)
    if abs(radians) < 0.000001:
        return Mat33.identity()
    else:

        axis = normalize(axis)

        K = Mat33(
            0.0, -axis[2], axis[1],
            axis[2], 0.0, -axis[0],
            -axis[1], axis[0], 0.0
        )

        return Mat33.identity() + math.sin(radians) * K + (1.0 - math.cos(radians)) * dot(K, K)

        """
        u = axis / radians

        c = math.cos(radians)
        s = math.sin(radians)

        return Mat33(
            u[0] * u[0] * (1.0 - c) + c,
            u[0] * u[1] * (1.0 - c) - u[2] * s,
            u[0] * u[2] * (1.0 - c) + u[1] * s,

            u[1] * u[0] * (1.0 - c) + u[2] * s,
            u[1] * u[1] * (1.0 - c) + c,
            u[1] * u[2] * (1.0 - c) - u[0] * s,

            u[2] * u[0] * (1.0 - c) - u[1] * s,
            u[2] * u[1] * (1.0 - c) + u[0] * s,
            u[2] * u[2] * (1.0 - c) + c
        )
        """


def rotation_to_axis(rot: Mat33) -> Vec3:

    ang = math.acos(clip(0.5 * (tr(rot) - 1.0), -1.0, 1.0))

    # For small angles, prefer series expansion to division by sin(theta) ~ 0
    if abs(ang) < 0.00001:
        scale = 0.5 + ang * ang / 12.0
    else:
        scale = 0.5 * ang / math.sin(ang)

    return Vec3(
        rot.get(2, 1) - rot.get(1, 2),
        rot.get(0, 2) - rot.get(2, 0),
        rot.get(1, 0) - rot.get(0, 1)
    ) * scale


def euler_to_rotation(pitch_yaw_roll: Vec3) -> Mat33:
    cp = math.cos(pitch_yaw_roll[0])
    sp = math.sin(pitch_yaw_roll[0])
    cy = math.cos(pitch_yaw_roll[1])
    sy = math.sin(pitch_yaw_roll[1])
    cr = math.cos(pitch_yaw_roll[2])
    sr = math.sin(pitch_yaw_roll[2])

    rotation = Mat33()

    # front direction
    rotation.set(0, 0, cp * cy)
    rotation.set(1, 0, cp * sy)
    rotation.set(2, 0, sp)

    # left direction
    rotation.set(0, 1, cy * sp * sr - cr * sy)
    rotation.set(1, 1, sy * sp * sr + cr * cy)
    rotation.set(2, 1, -cp * sr)

    # up direction
    rotation.set(0, 2, -cr * cy * sp - sr * sy)
    rotation.set(1, 2, -cr * sy * sp + sr * cy)
    rotation.set(2, 2, cp * cr)

    return rotation


def rotation_to_euler(rotation: Mat33) -> Vec3:
    return Vec3(
        math.atan2(rotation.get(2, 0), norm(Vec3(rotation.get(0, 0), rotation.get(1, 0)))),
        math.atan2(rotation.get(1, 0), rotation.get(0, 0)),
        math.atan2(-rotation.get(2, 1), rotation.get(2, 2))
    )


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


def proj_onto(src: Vec3, dir: Vec3) -> Vec3:
    """
    Returns the vector component of src that is parallel with dir, i.e. the projection of src onto dir.
    """
    try:
        return (dot(src, dir) / dot(dir, dir)) * dir
    except ZeroDivisionError:
        return Vec3()


def proj_onto_size(src: Vec3, dir: Vec3) -> float:
    """
    Returns the size of the vector that is the project of src onto dir
    """
    try:
        dir_n = normalize(dir)
        return dot(src, dir_n) / dot(dir_n, dir_n)  # can be negative!
    except ZeroDivisionError:
        return norm(src)


def rotated_2d(vec: Vec3, ang: float) -> Vec3:
    c = math.cos(ang)
    s = math.sin(ang)
    return Vec3(c * vec.x - s * vec.y,
                s * vec.x + c * vec.y)


def curve_from_arrival_dir(src, target, arrival_direction, w=1):
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


def bezier(t: float, points: list) -> Vec3:
    """
    Returns a point on a bezier curve made from the given controls points
    """
    n = len(points)
    if n == 1:
        return points[0]
    else:
        return (1 - t) * bezier(t, points[0:-1]) + t * bezier(t, points[1:n])


def is_closer_to_goal_than(a: Vec3, b: Vec3, team_index):
    """ Returns true if a is closer than b to goal owned by the given team """
    return (a.y < b.y, a.y > b.y)[team_index]


# Unit tests
if __name__ == "__main__":
    assert clip(12, -2, 2) == 2
    assert clip(-20, -5, 3) == -5
    assert angle_between(Vec3(x=1), Vec3(y=1)) == math.pi / 2
    assert angle_between(Vec3(y=1), Vec3(y=-1, z=1)) == 0.75 * math.pi
    assert norm(dot(axis_to_rotation(Vec3(x=-math.pi)), Vec3(y=1)) - Vec3(y=-1)) < 0.000001
    assert norm(dot(axis_to_rotation(Vec3(y=0.5*math.pi)), Vec3(z=1)) - Vec3(x=-1)) < 0.000001
    assert norm(dot(axis_to_rotation(Vec3(z=math.pi)), Vec3(x=1)) - Vec3(x=-1)) < 0.000001
    pyr = Vec3(0.5, 0.2, -0.4)
    assert norm(rotation_to_euler(euler_to_rotation(pyr)) - pyr) < 0.000001
