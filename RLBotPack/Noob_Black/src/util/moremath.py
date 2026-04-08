from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.orientation import Orientation, relative_location
from util.vec import Vec3

import math

def get_dist_from_wall(pos):
    return min(4096 - abs(pos.x), 5120 - abs(pos.y))
def ball_from_ground(og_pos, pos):
    dx = 4096 - abs(pos.x)
    dy = 5120 - abs(pos.y)
    if dx < dy:
        return Vec3(sign(pos.x) * (4096 + pos.z), pos.y, 0)
    else:
        return Vec3(pos.x, sign(pos.y) * (5120 + pos.z), 0)
def car_flat(pos):
    return pos.flat()
def ball_x_to_y(og_pos, pos):
    dx = 4096 - abs(pos.x)
    dy = 5120 - abs(pos.y)
    if dx < dy:
        return Vec3(sign(pos.x) * 4096, pos.y, pos.z)
    else:
        og_x = sign(og_pos.x)
        return Vec3(og_x * 4096, sign(pos.y) * (5120 + abs(pos.x - og_x * 4096)), pos.z)
def car_xwall(pos):
    return Vec3(sign(pos.x) * 4096, pos.y, pos.z)
def ball_y_to_x(og_pos, pos):
    dx = 4096 - abs(pos.x)
    dy = 5120 - abs(pos.y)
    if dx < dy:
        og_y = sign(og_pos.y)
        return Vec3(sign(pos.x) * (4096 + abs(pos.y - og_y * 5120)), og_y * 5120, pos.z)
    else:
        return Vec3(pos.x, sign(pos.y) * 5120, pos.z)
def car_ywall(pos):
    return Vec3(pos.x, sign(pos.y) * 5120, pos.z)
# Direction of position (position(Vec3))
def dir_convert(pos):
    if pos.length() > 0:
        return pos.normalized()
    else:
        return Vec3(0, 0, 0)
# Return a value with limitations
def clamp(x, m, M):
    if x < m:
        return m
    elif x > M:
        return M
    return x
# Divide numbers without division by 0
def safe_div(x):
    if x == 0:
        return math.inf
    else:
        return 1 / x
# Get the angle between two places
def get_angle(p1, p2):
    try:
        return p1.ang_to(p2)
    except:
        return 0
def car_dir(pitch, yaw):
    return Vec3(math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch))
def circle_dir(pitch, yaw, roll):
    cp = math.cos(pitch)
    cy = math.cos(yaw)
    cr = math.cos(-roll)
    sp = math.sin(pitch)
    sy = math.sin(yaw)
    sr = math.sin(-roll)
    return Vec3(sy * sr - cy * sp * cr, -cy * sr - sy * sp * cr, cp * cr)

def sign(v, pref = 0):
    if v != 0:
        return bool(v > 0) - bool(v < 0)
    else:
        return bool(pref > 0) - bool(pref < 0)

def solve_quadratic(a, b, c, ans, side):
    rt = (ans - c) / a + b**2 / (4 * a**2)
    if rt < 0:
        return None
    else:
        return -b / (2 * a) + math.sqrt(rt) * sign(side)
# Get the amount of time taken before the next bounce
def next_bounce_horizontal(pos, vel, height):
    def get_smallest(li):
        smallest = 0
        for i in range(len(li)):
            if li[i] < li[smallest]:
                smallest = i
        return li[smallest]
    pred_x = (4096 - height - pos.x * sign(vel.x)) * safe_div(vel.x) * sign(vel.x)
    pred_y = (5120 - height - pos.y * sign(vel.y)) * safe_div(vel.y) * sign(vel.y)
    return get_smallest([pred_x, pred_y])
# Get the amount of time taken before the next bounce
def next_bounce(pos, vel, height, g):
    def solve_quadratic(a, b, c, ans, side):
        rt = (ans - c) / a + b**2 / (4 * a**2)
        if rt < 0:
            return None
        else:
            return -b / (2 * a) + math.sqrt(rt) * sign(side)
    def get_smallest(li):
        smallest = 0
        for i in range(len(li)):
            if li[i] < li[smallest]:
                smallest = i
        return li[smallest]
    pred_x = (4096 - height - pos.x * sign(vel.x)) * safe_div(vel.x) * sign(vel.x)
    pred_y = (5120 - height - pos.y * sign(vel.y)) * safe_div(vel.y) * sign(vel.y)
    pred_z1 = solve_quadratic(-g / 2, vel.z, pos.z, height, 1)
    if pred_z1 == None:
        pred_z1 = 0
    pred_z2 = solve_quadratic(-g / 2, vel.z, pos.z, 2044 - height, -1)
    if pred_z2 == None:
        pred_z2 = math.inf
    return get_smallest([pred_z1, pred_x, pred_y, pred_z2])
# Get the controls (Intended point direction(Vec3), Current point direction(Vec3))
def get_aerial_control(dir, orig):
    # The problem
    ref_pitch = orig.pitch
    target_pitch = math.asin(dir.z)
    target_yaw = math.acos(dir.x * safe_div(Vec3(dir.x, dir.y, 0).length())) * sign(dir.y)
    offset_yaw = target_yaw - orig.yaw
    # Extra variables
    dist = math.sqrt((math.cos(ref_pitch) - math.cos(target_pitch) * math.cos(offset_yaw))**2 + (math.cos(target_pitch) * math.sin(offset_yaw))**2 + (math.sin(ref_pitch) - math.sin(target_pitch))**2)
    travel_angle = math.asin(dist / 2) * 2
    # Breakdown
    aa = math.cos(ref_pitch) * math.cos(travel_angle)
    ab = math.sin(ref_pitch) * math.sin(travel_angle)
    ac = math.cos(target_pitch) * math.cos(offset_yaw)
    ar_1 = (aa - ac) * safe_div(ab)

    ad = math.sin(travel_angle)
    ae = math.cos(target_pitch) * math.sin(offset_yaw)
    ar_2 = ae * safe_div(ad)

    af = math.sin(ref_pitch) * math.cos(target_pitch)
    ag = math.cos(ref_pitch) * math.sin(travel_angle)
    ah = math.sin(target_pitch)
    ar_3 = -(af - ah) * safe_div(ag)
    # Solution
    if abs(ar_1) <= 1:
        found_angle = math.acos(ar_1)
    elif abs(ar_3) <= 1:
        found_angle = math.acos(ar_3)
    else:
        found_angle = 0
        if False:
            print("B: " + str(travel_angle) + ", Ref(p): " + str(ref_pitch) + ", Target(p): " + str(target_pitch) + ", Offset(y): " + str(offset_yaw))
    return found_angle * sign(abs(ad * math.sin(found_angle) - ae) - abs(ad * math.sin(-found_angle) - ae))
def new_jump_time_wall(h, double = 0):
    single_time = -(-h - 7) / 538.9887109375
    if single_time >= 24 / 120:
        if single_time >= 25 / 120 and double > 0:
            if double == 1:
                return -(-h - 407 / 6) / 830.9887109375, 3
            else:
                return -(-h - 667 / 6) / 1038.9887109375, 2
        else:
            return single_time, 1
    else:
        s_eq = solve_quadratic(717.3359375, 272.7626953125, 17.671875, h, 1)
        if s_eq == None:
            return 0, 1
        else:
            return s_eq, 1

def new_max_jump_height(double):
    x = -(564.9931640625 + 292 * bool(double)) / (-325.0556640625 * 2)
    return -325.0556640625 * x**2 + (564.9931640625 + 292 * bool(double)) * x + -11.6591796875 - 292 * 25 / 120 * bool(double)