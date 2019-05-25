import math

try:
    import numpy as np
except ImportError:
    try:
        from pip import main as pipmain
    except ImportError:
        from pip._internal import main as pipmain
        pipmain(['install', 'numpy'])
    try:
        import numpy as np
    except ImportError:
        raise ImportError("Failed to install numpy automatically, please install manually using: 'pip install numpy'")


U180 = 32768
U90 = U180 / 2
PI = math.pi
SQ2 = math.sqrt(2)

UP = np.array([0, 0, 1])
RI = np.array([-1, 0, 0])

GRAVITY = np.array([0, 0, -650])

HITBOX = 42, 59, 18
HITBOX_OFFSET = np.array([0, 14, 21])


''' Utility functions sorted in alphabetical order '''


def a2(v):
    """Converts a Vector or normal list to a numpy array of size 2."""
    try:
        a = np.array([v[0], v[1]])
    except TypeError:
        a = np.array([v.x, v.y])
    return a


def a3(V):
    """Converts a Vector, rotator or normal list to a numpy array of size 3."""
    try:
        return np.array([V[0], V[1], V[2]])
    except TypeError:
        try:
            return np.array([V.x, V.y, V.z])
        except AttributeError:
            return np.array([V.Pitch, V.Yaw, V.Roll])


def a3l(L):
    """Converts List to numpy array"""
    return np.array([L[0], L[1], L[2]])


def a3r(R):
    """Converts Rotator to numpy array"""
    return np.array([R.pitch, R.yaw, R.roll])


def a3v(V):
    """Converts Vector3 to numpy array"""
    return np.array([V.x, V.y, V.z])


def ang_dif(a1, a2, pi=PI):
    """Absolute difference between two angles"""
    return abs(Range180(a1 - a2, pi))


def angle(a, b):
    """Returns angle between two 2d points in radians"""
    return math.atan2(a[1] - b[1], a[0] - b[0])


def angle2(a, b):
    """Returns angle between two 2d points in radians"""
    return math.atan2(a[0] - b[0], a[1] - b[1])


def box_collision(local_point, box=HITBOX, offset=HITBOX_OFFSET):
    """point of contact in local coordinates"""
    point = local_point - offset
    return np.array([Range(point[0], box[0]), Range(point[1], box[1]), Range(point[2], box[2])]) + offset


def cartesian(r, a, i):
    """Converts from spherical to cartesian coordinates."""
    x = r * math.sin(i) * math.cos(a)
    y = r * math.sin(i) * math.sin(a)
    z = r * math.cos(i)
    return np.array([x, y, z])


def circles_tangent(c1, c1r, c1s, c2, c2r, c2s):
    """Return line tangent to two circles"""
    out = sign(c1s) != sign(c2s)
    if c1r != c2r or not out:
        pc2t = tangent_point(c2, c2r - c1r * sign(out), c1, c2s)
        c2t = set_dist(a2(c2), pc2t, c2r * sign(c2r > c1r or not out))
        c1t = a2(c1) + c2t - pc2t
    else:
        c2t = set_dist_ang(a2(c2), a2(c1), c2r, -PI / 2 * sign(c2s))
        c1t = a2(c1) + c2t - a2(c2)
    return c1t, c2t


def det(a, b):
    return a[0] * b[1] - a[1] * b[0]


def dist2d(a, b=[0, 0]):
    """Distance/Magnitude in 2d."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def dist3d(a, b=[0, 0, 0]):
    """Distance/Magnitude in 3d."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def line_intersect(line1, line2):
    """Returns intersection point coordinates of 2 lines in 2d"""
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])
    div = det(xdiff, ydiff)
    if div == 0:
        div = 1
    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y


def local(tL, oL, oR, Urot=True):
    """Transforms global/world into local coordinates."""
    L = tL - oL
    if Urot:
        pitch = oR[0]
        yaw = Range180(oR[1] - PI / 2, PI)
        roll = oR[2]
        R = [-pitch, -yaw, -roll]
    else:
        R = -oR
    x, y = rotate2D(L[0], L[1], R[1])
    y, z = rotate2D(y, L[2], R[0])
    x, z = rotate2D(x, z, R[2])
    return np.array([x, y, z])


def local_radius(x, y):
    """Returns radius of the circle going through a point given it's local coordinates."""
    if x != 0:
        return (x**2 + y**2) / abs(2 * x)
    else:
        return y**2


def mid_ang(a1, a2, pi=PI):
    """Middle between two angles"""
    return Range180(Range180(a1 - a2, pi) / 2 + a2, pi)


def mid_vect(v1, v2):
    return normalize((normalize(v1) + normalize(v2)) / 2)


def normalize(A):
    """Resizes the vector length to 1"""
    mag = np.linalg.norm(A)
    if mag == 0:
        mag = 1
    return A / mag


def Range(value, max_value):
    """Constrains value to [-max_value, max_value] range"""
    if abs(value) > max_value:
        value = math.copysign(max_value, value)
    return value


def Range180(a, pi=PI):
    """Limits any angle a to [-pi, pi] range, example: Range180(270, 180) = -90"""
    if abs(a) >= 2 * pi:
        a -= abs(a) // (2 * pi) * 2 * pi * sign(a)
    if abs(a) > pi:
        a -= 2 * pi * sign(a)
    return a


def Range360(a, pi=PI):
    """Limits any angle to [0, 360] range"""
    return a - (a // (2 * pi)) * 2 * pi


def relative_angle(a, b, o):
    """Relative angle between two points relative to an origin"""
    return Range180(angle2(a, o) - angle2(b, o), PI)


def rotate2D(x, y, ang):
    """Rotates a 2d vector clockwise by an angle in radians."""
    x2 = x * math.cos(ang) - y * math.sin(ang)
    y2 = y * math.cos(ang) + x * math.sin(ang)
    return x2, y2


def set_dist(a, b, dist=1):
    """Returns point distance away from a towards b"""
    return normalize(b - a) * dist + a


def set_dist_ang(a, b, dist, ang=0):
    """Returns point distance and angle away from a towards b"""
    c = normalize(b - a) * dist
    cr2d = rotate2D(*c[:2], ang)
    cr = cr2d if len(a) == 2 else a3([*cr2d, c[2]])
    return cr + a


def sign(x):
    """Retuns 1 if x > 0 else -1. > instead of >= so that sign(False) returns -1"""
    return 1 if x > 0 else -1


def Sign(x):
    """Retuns 1 if x >= 0 else -1."""
    return 1 if x >= 0 else -1


def spherical(x, y, z, Urot=True):
    """Converts from cartesian to spherical coordinates."""
    d = math.sqrt(x * x + y * y + z * z)
    if d != 0:
        i = math.acos(z / d)
    else:
        i = 0
    a = math.atan2(x, y)
    if Urot:
        return d, -a / PI, Range180(i - PI / 2, PI) / PI
    else:
        return d, a, i


def tangent_point(circle, circle_radius, point, angle_sign=1):
    """Circle tangent passing through point, angle sign + if clockwise else - """

    circle2d, point2d = a2(circle), a2(point)

    circle_distance = dist2d(circle2d, point2d) + 1e-9

    relative_angle = math.acos(Range(circle_radius / circle_distance, 1))

    point_angle = angle(point2d, circle2d)

    tangent_angle = (point_angle - relative_angle * sign(angle_sign))

    tangentx = math.cos(tangent_angle) * circle_radius + circle2d[0]
    tangenty = math.sin(tangent_angle) * circle_radius + circle2d[1]

    return a2([tangentx, tangenty])


def turning_radius(speed):
    """Minimum turning radius given speed"""
    return -6.901E-11 * speed**4 + 2.1815E-07 * speed**3 - 5.4437E-06 * speed**2 + 0.12496671 * speed + 157


def turning_speed(radius):
    """Maximum speed given turning radius"""
    return 10.219 * radius - 1.75404E-2 * radius**2 + 1.49406E-5 * radius**3 - 4.486542E-9 * radius**4 - 1156.05


def world(L, oL, oR, Urot=True):
    """transforms local into global/world coordinates"""
    tL = np.zeros(3)
    if Urot:
        pitch = oR[0]
        yaw = Range180(oR[1] - PI / 2, PI)
        roll = oR[2]
        R = np.array([pitch, yaw, roll])
    else:
        R = oR
    tL[0], tL[2] = rotate2D(L[0], L[2], R[2])
    tL[1], tL[2] = rotate2D(L[1], tL[2], R[0])
    tL[0], tL[1] = rotate2D(tL[0], tL[1], R[1])
    tL = tL + oL
    return tL
