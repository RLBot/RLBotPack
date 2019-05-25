import math
import numpy as np
from functools import reduce

#  A utility wrapper around numpy.array
# mainly to name things how I like them

def Vec2(x, y):
    return np.array([x,y], dtype=float)
def Vec3(x, y, z):
    return np.array([x,y,z], dtype=float)

UCONST_Pi = 3.1415926
URotation180 = float(32768)
URotationToRadians = UCONST_Pi / URotation180
tau = 2*np.pi
DEGREES_TO_RADIANS = tau / 360.0
RADIANS_TO_DEGREES = 360.0 / tau

UP = np.array([0.0, 0.0, 1.0])
UP.flags.writeable = False


# Usual vector functions
cross = np.cross
sqrt = np.sqrt
equal = np.array_equal
dot = np.dot
def mag(vec):
    ''' magnitude/length of a vector '''
    return np.linalg.norm(vec)
def dist(vec1, vec2):
    return mag(vec2 - vec1)
def normalize(vec):
    magnitude = mag(vec)
    if not magnitude: return vec
    return vec / magnitude
def clamp(x, bot, top):
    return min(top, max(bot, x))
def clamp01(x):
    return clamp(x, 0.0, 1.0)
def clamp11(x):
    return clamp(x, -1.0, 1.0)
def lerp(v0, v1, t):  # linear interpolation
  return (1 - t) * v0 + t * v1;
def is_close(v0, v1):
    return all(np.isclose(v0, v1))

# less common stuff
def xy_only(vec3):
    return vec3[:2]
def z0(vec2):  # sets the z axis of the vector to zero.
    return Vec3(vec2[0], vec2[1], 0.0)
def get_quadrant(vec3):
    return Vec3(
        1 if vec3[0] >= 0 else -1,
        1 if vec3[1] >= 0 else -1,
        1 if vec3[2] >= 0 else -1,
    )

###### Angle and rotation stuff ####

def vec2angle(vec2):
    '''
    >>> vec2angle(Vec2(0, 1))
    1.5707963267948966
    '''
    return math.atan2(vec2[1], vec2[0])
def clockwise90degrees(vec2):
    # Clockwise (away from Y=up)
    return clockwise_matrix(tau/4).dot(vec2)
def closest180(angle):
    return ((angle+UCONST_Pi) % (2*UCONST_Pi)) - UCONST_Pi
def positive_angle(angle):
    return angle % tau
def clockwise_matrix(radians):
    '''
    >>> clockwise_matrix(tau/4).dot(Vec2(1,0))
    [0.0, 1.0]
    '''
    t = radians
    return np.array([
        [ np.cos(t), -np.sin(t)],
        [ np.sin(t),  np.cos(t)],
    ])
def clockwise_angle(a, b):
    '''
    >>> clockwise_angle(Vec2(1, 0), Vec2(0, -1))
    -1.5707963267948966
    '''
    # Note: x=right, y=up
    dot = a.dot(b)      # dot product
    det = np.linalg.det([a, b])      # determinant
    return math.atan2(det, dot)  # atan2(y, x) or atan2(sin, cos)
def clockwise_angle_abc(a, b_center, c):
    return clockwise_angle(a-b_center, c-b_center)
# Angle around `b` with direction specified by `clockwise`
def directional_angle(a,b,c, clockwise):
    '''
    >>> directional_angle(Vec2(0,0), Vec2(-1,0), Vec2(-1, 1), True)
    1.5707963267948966
    >>> directional_angle(Vec2(0,0), Vec2(-1,0), Vec2(-1, 1), False)
    4.712388873205104
    '''
    angle = clockwise_angle_abc(a, b, c)
    if not clockwise:
        angle *= -1
    return positive_angle(angle)
def reflect(vec, normal):
    return vec - 2*dot(vec, normal) * normal

def struct_vector3_to_numpy(vec):
    return Vec3(vec.X, vec.Y, vec.Z)

def rotation_to_mat(rotator):
    return to_rotation_matrix(
        URotationToRadians * rotator.Pitch,
        URotationToRadians * rotator.Yaw,
        URotationToRadians * rotator.Roll
    )

def to_rotation_matrix(pitch, yaw, roll):
    # Note: Unreal engine coordinate system
    y=pitch
    cosy = math.cos(y)
    siny = math.sin(y)
    mat_pitch = np.array(
            [[cosy, 0, -siny],
             [0, 1, 0],
             [siny, 0, cosy]])

    z=yaw
    cosz = math.cos(z)
    sinz = math.sin(z)
    mat_yaw = np.array(
            [[cosz, -sinz, 0],
             [sinz, cosz, 0],
             [0, 0, 1]])

    x=roll
    cosx = math.cos(x)
    sinx = math.sin(x)
    mat_roll = np.array(
            [[1, 0, 0],
             [0, cosx, sinx],
             [0, -sinx, cosx]])

    return reduce(np.dot, [mat_yaw, mat_pitch, mat_roll])

