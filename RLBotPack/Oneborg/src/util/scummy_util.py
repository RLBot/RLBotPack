from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import math, random

'''
Section: Numeral Mathematics
'''
# Solve a quadratic equation
def solve_quadratic(a, b, c, ans, side):
    return -b / (2 * a) + math.sqrt(b**2 / (4 * a**2) - (c - ans) / a) * sign(side)
# Division without risk of division by 0 error (divided by(Number))
def safe_div(x):
    if x != 0:
        return 1 / x
    else:
        return math.inf
# Set limits on a value (value(Number), min value(Number), max value(Number))
def clamp(x, m, M):
    if x >= M:
        return M
    elif x <= m:
        return m
    else:
        return x
# Direction of a number (value(Number))
def sign(x):
    if x < 0:
        return -1
    elif x > 0:
        return 1
    else:
        return 0
# Direction of a number with preference (value(Number), preference(Number))
def pref_sign(x, pref):
    if x < 0:
        return -1
    elif x > 0:
        return 1
    elif pref < 0:
        return -1
    elif pref > 0:
        return 1
    else:
        return 0
# Flip val
def flip_value(x):
    if x > 0.5:
        return 1
    elif x < -0.5:
        return -1
    else:
        return 0
'''
Section: Vector Mathematics
'''
# Get direction with offset
def direction_offset(dir, circlev, offset):
    angle_pitch = math.asin(dir.z)
    angle_yaw = math.acos(dir.x * safe_div(Vec3(dir.x, dir.y, 0).length())) * sign(dir.y)
    if circlev - Vec3(0, 0, sign(circlev.z)) == Vec3(0, 0, 0):
        angle_yaw += offset * sign(circlev.z)
    elif circlev - Vec3(sign(circlev.x), 0, 0) == Vec3(0, 0, 0):
        angle_pitch += offset * sign(circlev.x)
    return Vec3(math.cos(angle_yaw) * math.cos(angle_pitch), math.sin(angle_yaw) * math.cos(angle_pitch), math.sin(angle_pitch))
# Get acceleration
def get_accel(vel):
    if vel < 0:
        return 3500
    elif vel <= 1400:
        return 1600 - vel * 1440 / 1400
    elif vel <= 1410:
        return (1410 - vel) * 16
    else:
        return 0
# Plane smoothening
def flat_on_surface(pos1, pos2, dropshot):
    offset = pos1 - surface_pos(pos1, dropshot)
    offset = dir_convert(offset)
    pitch = math.asin(offset.z)
    yaw = math.acos(offset.x * safe_div(Vec3(offset.x, offset.y, 0).length())) * sign(offset.y)
    Vec3(-math.cos(yaw) * math.sin(pitch) * math.cos(roll) + math.sin(yaw) * math.sin(roll), -math.sin(yaw) * math.sin(pitch) * math.cos(roll) - math.cos(yaw) * math.sin(roll), math.cos(roll) * math.cos(pitch))
# Drive outside the goal
def outside_goal(pos1, pos2):
    if abs(pos1.y) >= 5090 and pos1.z < 40:
        y_offset = abs(pos2.y - pos1.y)
        indented = abs(pos1.y) - 5090
        x_offset = pos2.x - pos1.x
        return Vec3(clamp(pos1.x + x_offset * indented * safe_div(y_offset), -800, 800), sign(pos1.y) * 5090, pos1.z)
    else:
        return pos2
# Direction of position (position(Vec3))
def dir_convert(pos):
    return pos * safe_div(pos.length())
# Get the angle between two places (position 1(Vec3), position 2(Vec3))
def get_angle(p1, p2):
    d = (p1 * safe_div(p1.length()) - p2 * safe_div(p2.length())).length()
    angle = 2 * math.asin(d / 2)
    return angle
# Position on Surface (position(Vec3), dropshot mode(Bool))
def surface_pos(pos, dropshot):
    nearest_dist = math.inf
    new_pos = pos
    if dropshot == True:
        b_dist = Vec3(pos.x, pos.y, 0).length()
        if b_dist > 0:
            ball_angle = math.acos(pos.x * safe_div(b_dist)) * sign(pos.y)
            surface_angle = math.floor(ball_angle / math.pi * 3) * math.pi / 3 + math.pi / 6
            if 4555 - b_dist * math.cos(ball_angle - surface_angle) < nearest_dist:
                new_pos = Vec3(4555 * math.cos(surface_angle), 4555 * math.sin(surface_angle), pos.z) + Vec3(math.cos(ball_angle) * b_dist, math.sin(ball_angle) * b_dist, 0) * safe_div(math.cos(ball_angle - surface_angle)) - Vec3(math.cos(surface_angle) * b_dist, math.sin(surface_angle) * b_dist, 0)
                nearest_dist = 4555 - b_dist * math.cos(ball_angle - surface_angle)
    else:
        if 4096 - clamp(abs(pos.x), 0, 4096) < nearest_dist:
            new_pos = Vec3(sign(pos.x) * 4096, pos.y, pos.z)
            nearest_dist = 4096 - clamp(abs(pos.x), 0, 4096)
        if 5120 - clamp(abs(pos.y), 0, 5120) < nearest_dist and (abs(pos.x) > 846 or pos.z > 596):
            new_pos = Vec3(pos.x, sign(pos.y) * 5120, pos.z)
            nearest_dist = 5120 - clamp(abs(pos.y), 0, 5120)
    if pos.z < nearest_dist:
        new_pos = Vec3(pos.x, pos.y, 0)
        nearest_dist = pos.z
    return new_pos
# Position on Surface (position(Vec3), dropshot mode(Bool))
def surface_pos_two(pos, from_pos, freshhold, dropshot):
    nearest_dist = math.inf
    new_pos = pos
    from_posN = surface_pos(from_pos, dropshot)
    # First check: If both can be placed on the same surface with reasonable freshhold
    if dropshot == True:
        b_dist = Vec3(pos.x, pos.y, 0).length()
        from_b_dist = Vec3(from_pos.x, from_pos.y, 0).length()
        if b_dist > 0:
            ball_angle = math.acos(pos.x * safe_div(b_dist)) * sign(pos.y)
            from_angle = math.acos(from_pos.x * safe_div(from_b_dist)) * sign(from_pos.y)
            surface_angle = math.floor(ball_angle / math.pi * 3) * math.pi / 3 + math.pi / 6
            from_surface_angle = math.floor(from_angle / math.pi * 3) * math.pi / 3 + math.pi / 6
            if 4555 - b_dist * math.cos(ball_angle - surface_angle) <= freshhold and 4555 - from_b_dist * math.cos(from_angle - from_surface_angle) < nearest_dist:
                new_pos = Vec3(4555 * math.cos(surface_angle), 4555 * math.sin(surface_angle), pos.z) + Vec3(math.cos(ball_angle) * b_dist, math.sin(ball_angle) * b_dist, 0) * safe_div(math.cos(ball_angle - surface_angle)) - Vec3(math.cos(surface_angle) * b_dist, math.sin(surface_angle) * b_dist, 0)
                nearest_dist = 4555 - b_dist * math.cos(ball_angle - surface_angle)
    else:
        if 4096 - clamp(abs(pos.x), 0, 4096) <= freshhold and from_posN.x == sign(pos.x) * 4096:
            new_pos = Vec3(sign(pos.x) * 4096, pos.y, pos.z)
            nearest_dist = 4096 - clamp(abs(pos.x), 0, 4096)
        if 5120 - clamp(abs(pos.y), 0, 5120) <= freshhold and (abs(pos.x) > 846 or pos.z > 596) and from_posN.y == sign(pos.y) * 5120:
            new_pos = Vec3(pos.x, sign(pos.y) * 5120, pos.z)
            nearest_dist = 5120 - clamp(abs(pos.y), 0, 5120)
    if pos.z <= freshhold and from_posN.z == 0:
        new_pos = Vec3(pos.x, pos.y, 0)
        nearest_dist = pos.z
    if nearest_dist != math.inf:
        return new_pos
    # Second check
    new_pos = surface_pos(pos, dropshot)
    return new_pos
# Driving path for wall transitions
def wall_transition_path(pos1, pos2, dropshot):
    rp1 = surface_pos(pos1, dropshot)
    rp2 = surface_pos(pos2, dropshot)
    if dropshot == True:
        if rp1.z == 0:
            if rp2.z == 0:
                return rp2
            else:
                b_dist = Vec3(rp2.x, rp2.y, 0).length()
                ball_angle = math.acos(rp2.x * safe_div(b_dist)) * sign(rp2.y)
                surface_angle = math.floor(ball_angle / math.pi * 3) * math.pi / 3 + math.pi / 6
                return Vec3(rp2.x, rp2.y, 0) + Vec3(rp2.z * math.cos(surface_angle), rp2.z * math.sin(surface_angle), 0)
        return rp2
    else:
        if rp1.z == 0:
            if abs(rp2.x) == 4096:
                return Vec3((4096 + rp2.z) * sign(rp2.x), rp2.y, rp1.z)
            elif abs(rp2.y) == 5120:
                return Vec3(rp2.x, (5120 + abs(rp2.z)) * sign(rp2.y), rp1.z)
        elif abs(rp1.x) == 4096:
            if rp2.z == 0:
                return Vec3(rp1.x, rp2.y, -abs(rp1.x - rp2.x))
            elif abs(rp2.y) == 5120:
                return Vec3(rp1.x, (5120 + abs(rp2.x - rp1.x)) * sign(rp2.y), rp2.z)
        elif abs(rp1.y) == 5120:
            if rp2.z == 0:
                return Vec3(rp2.x, rp1.y, -abs(rp1.y - rp2.y))
            elif abs(rp2.x) == 4096:
                return Vec3((4096 + abs(rp2.y - rp1.y)) * sign(rp2.x), rp1.y, rp2.z)
        return rp2
# Direction to point (position ref(Vec3), point to(Vec3))
def dir_to_point(pos1, pos2):
    return (pos2 - pos1) * safe_div((pos2 - pos1).length())
# Determine when the car can intersect a bounce (offset time(Number), self.get_ball_prediction_struct(), car location(Vec3), car velocity(Vec3), max ball distance from surface allowed(Number), distance to point to target(Number), target(Vec3), dropshot mode(Bool), packet)
def next_bounce(t_offset, ball_prediction, pos, vel, g_offset, target, dropshot, packet):
    ref = surface_pos(pos, dropshot)
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    for i in range(1, 101):
        bp = predict_ball(t_offset + i / 20)
        pbp = predict_ball(t_offset + (i - 1) / 20)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), target) * g_offset
        point_pos = wall_transition_path(pos, point_pos, dropshot)
        if (point_pos - ref).length() <= vel * i / 20 and bp.physics.velocity.z >= 0 and pbp.physics.velocity.z <= 0:
            return i / 20
    return 0
# Determine when the car can intersect the ball (offset time(Number), self.get_ball_prediction_struct(), car location(Vec3), car velocity(Vec3), max ball distance from surface allowed(Number), distance to point to target(Number), target(Vec3), dropshot mode(Bool), packet)
def intersect_time(t_offset, ball_prediction, pos, vel, height_threshold, g_offset, target, dropshot, surface, boost, packet):
    ref = pos
    if surface == True:
        ref = surface_pos(ref, dropshot)
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    # Ball prediction
    for i in range(1, 101):
        bp = predict_ball(t_offset + i / 20)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), target) * g_offset
        point_pos2 = point_pos
        if surface == True:
            point_pos = wall_transition_path(pos, point_pos, dropshot)
        if True:
            if (point_pos - ref).length() <= vel * i / 20 and (point_pos2 - surface_pos(point_pos2, dropshot)).length() <= height_threshold:
                return i / 20
        else:
            if (point_pos2 - ref).length() <= vel * i / 20 and (point_pos - surface_pos(point_pos, dropshot)).length() <= height_threshold:
                return i / 20
    return 0
# Determine when the car can intersect the ball (offset time(Number), self.get_ball_prediction_struct(), car location(Vec3), car velocity(Vec3), max ball distance from surface allowed(Number), distance to point to target(Number), target(Vec3), dropshot mode(Bool), packet)
def intersect_time_x(t_offset, ball_prediction, pos, vel, height_threshold, g_offset, target, dropshot, surface, boost, boost_strength, packet):
    ref = pos
    if surface == True:
        ref = surface_pos(ref, dropshot)
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    # Formulas for speed
    vel_after_boost = vel
    tv = 0
    # First step of acceleration
    a1 = 1440 / 1400
    b1 = (1600 + boost_strength) * 1400 / 1440
    b1n = 1600 * 1400 / 1440
    if vel < 1400:
        tv = -math.log(1 - vel / b1) / a1
    tc1 = -math.log(1 - 1400 / b1) / a1
    tc1n = -math.log(1 - 1400 / b1n) / a1
    # Second step of acceleration
    a2 = 16
    b2 = 1410 + boost_strength / 16
    b2n = 1410
    if vel < 1410 and tv == 0:
        tv = tc1 - math.log(1 - vel / b2) / a2 + math.log(1 - 1400 / b2) / a2
    tc2 = tc1 - math.log(1 - 1410 / b2) / a2 + math.log(1 - 1400 / b2) / a2
    # Added acceleration with boost
    if vel < 2300 and tv == 0:
        tv = tc2 - (1410 - vel) / boost_strength
    tc3 = tc2 + 534 / 595
    # Time with boost (Verifyably functional)
    tb = tv + boost / 100 * 3
    # Velocity with boost (Verifyably functional)
    velB = 0
    if tb < tc1:
        velB = (1 - math.e**(-a1 * tb)) * b1
    if tb < tc2 and velB == 0:
        velB = (1 - math.e**(-a2 * (tb - tc1 + math.log(1 - 1400 / b2) / a2))) * b2
    if tb < tc3 and velB == 0:
        velB = 1410 + boost_strength * (tb - tc2)
    if tb >= tc3 and velB == 0:
        velB = 2300
    # Ball prediction
    for i in range(1, 101):
        cc1, cc2, cc3, cc1n = clamp(tc1, 0, tb), clamp(tc2, 0, tb), clamp(tc3, 0, tb), clamp(tc1n, tb, math.inf)
        # Distance covered with boost
        dist_wb = b1 * ((math.e**(-a1 * 0) / a1 + 0) - (math.e**(-a1 * clamp(tv + i / 20, 0, cc1)) / a1 + clamp(tv + i / 20, 0, cc1))) + b2 * ((math.e**(-a2 * cc1) / a2 + cc1) - (math.e**(-a2 * clamp(tv + i / 20, cc1, cc2)) / a2 + clamp(tv + i / 20, cc1, cc2))) + 1410 * (clamp(tv + i / 20, cc2, cc3) - cc2) + (boost_strength / 2) * (clamp(tv + i / 20, cc2, cc3)**2 - cc2**2) + 2300 * (clamp(tv + i / 20, cc3, math.inf) - cc3)
        # Distance covered without boost
        dist_wob = velB * (clamp(tv + i / 20, tb, math.inf) - tb)
        
        
        bp = predict_ball(t_offset + i / 20)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), target) * g_offset
        point_pos2 = point_pos
        if surface == True:
            point_pos = wall_transition_path(pos, point_pos, dropshot)
        if True:
            if (point_pos - ref).length() <= dist_wb + dist_wob and (point_pos2 - surface_pos(point_pos2, dropshot)).length() <= height_threshold:
                return i / 20
        else:
            if (point_pos2 - ref).length() <= dist_wb + dist_wob and (point_pos - surface_pos(point_pos, dropshot)).length() <= height_threshold:
                return i / 20
    return 0
# Determine when the car is closest to the ball (offset time(Number), self.get_ball_prediction_struct(), car location(Vec3), car velocity(Vec3), max ball distance from surface allowed(Number), distance to point to target(Number), target(Vec3), dropshot mode(Bool), packet)
def nearest_intersection(t_offset, ball_prediction, pos, height_threshold, g_offset, target, dropshot, surface, packet):
    ref = pos
    nearest_t = 0
    nearest_dist = math.inf
    engaged = False
    if surface == True:
        ref = surface_pos(ref, dropshot)
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    for i in range(1, 101):
        bp = predict_ball(t_offset + i / 20)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), target) * g_offset
        point_pos2 = point_pos
        if (point_pos - surface_pos(point_pos, dropshot)).length() <= height_threshold:
            if engaged == True:
                if (point_pos - pos).length() < nearest_dist:
                    nearest_dist = (point_pos - pos).length()
                    nearest_t = i / 20
                else:
                    return nearest_t
            else:
                if (point_pos - pos).length() < nearest_dist and nearest_dist != math.inf:
                    engaged = True
                nearest_dist = (point_pos - pos).length()
                nearest_t = i / 20
    if engaged == True:
        return nearest_t
    else:
        return 0.05
'''
Section: Jumps
'''
def jump_time(h, double):
    if h <= 74.6:
        return -292 / 810 + math.sqrt(h / 405 + (292 / 810)**2), 1
    elif h <= -29.2 + 584 * 292 / 325 - 325 * 292**2 / 325**2:
        return 292 / 325 - math.sqrt(-h / 325 - 29.2 / 325 + (292 / 325)**2), 1
    elif h <= 876 * 438 / 325 - 325 * (438 / 325)**2 - 584 / 6 and double:
        return 438 / 325 - math.sqrt(-h / 325 + (438 / 325)**2 - 584 / 1950), 2
    else:
        return 0, 0
def jump_time_x(h, g, double):
    def fx(x):
        return (292 * 5 - g) / 2 * x**2 + 292 * x
    def hx(x):
        return -g / 2 * x**2 + 584 * x - 292 / 10
    def qx(x):
        return -g / 2 * x**2 + 876 * x - (365 / 3 - 292 / 10)
    if h <= fx(12 / 60):
        return solve_quadratic((292 * 5 - g) / 2, 292, 0, h, 1), 1
    elif h <= hx(584 / g):
        return solve_quadratic(-g / 2, 584, -292 / 10, h, -1), 1
    elif h <= qx(876 / g) and double:
        return solve_quadratic(-g / 2, 876, -(365 / 3 - 292 / 10), h, -1), 2
    else:
        return 0, 0
def max_jump_height(g, double):
    def hx(x):
        return -g / 2 * x**2 + 584 * x - 292 / 10
    def qx(x):
        return -g / 2 * x**2 + 876 * x - (365 / 3 - 292 / 10)
    if double:
        return qx(876 / g)
    else:
        return hx(584 / g)
'''
Section: Aerials
'''
# Get the direction to intersect the ball in the air (car location(Vec3), car velocity(Vec3), offset time(Number), self.get_ball_prediction_struct(), target(Vec3), boost quantity(Number), packet)
def aerial_dir(pos, vel, t_offset, ball_prediction, send_location, boost, offset, boost_power, gravity, begin_tick, search_dir, packet):
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    nearest_time = 0
    nearest_val = math.inf
    prev_disparity = -math.inf
    for i in range(begin_tick, (101 * (1 + sign(search_dir))) // 2, search_dir):
        t = i / 20
        bp = predict_ball(t_offset + t)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), send_location) * offset
        int_dist = ((pos + vel * t - Vec3(0, 0, gravity / 2) * t**2) - point_pos).length()
        if t <= boost * 3 / 100:
            if int_dist <= boost_power / 2 * t**2:
                return point_pos - (pos + vel * t - Vec3(0, 0, gravity / 2) * t**2), t + prev_disparity / (prev_disparity + boost_power / 2 * t**2 - int_dist) / 20
        prev_disparity = int_dist - boost_power / 2 * t**2
    return Vec3(predict_ball(t_offset).physics.location), 0
# Get the direction to intersect the ball in the air (car location(Vec3), car velocity(Vec3), offset time(Number), self.get_ball_prediction_struct(), target(Vec3), boost quantity(Number), packet)
def aerial_dir_x(pos, vel, t_offset, ball_prediction, send_location, boost, offset, boost_power, gravity, begin_tick, search_dir, front_dir, packet):
    def predict_ball(t):
        ball_in_future = find_slice_at_time(ball_prediction, t)
        if ball_in_future is not None:
            return ball_in_future
        else:
            return packet.game_ball
    nearest_time = 0
    nearest_val = math.inf
    prev_disparity = -math.inf
    for i in range(begin_tick, (101 * (1 + sign(search_dir))) // 2, search_dir):
        t = i / 20
        bp = predict_ball(t_offset + t)
        point_pos = Vec3(bp.physics.location) - dir_to_point(Vec3(bp.physics.location), send_location) * offset
        int_vector = point_pos - (pos + vel * t - Vec3(0, 0, gravity / 2) * t**2)
        t2 = t - get_angle(front_dir, int_vector) / 5.5
        int_dist = int_vector.length()
        if t <= boost * 3 / 100:
            if int_dist <= boost_power / 2 * t**2:
                return int_vector, t + prev_disparity / (prev_disparity + boost_power / 2 * t**2 - int_dist) / 20
        prev_disparity = int_dist - boost_power / 2 * t**2
    return Vec3(predict_ball(t_offset).physics.location), 0
# Control of aerial (Intended point direction(Vec3), Current point direction(Vec3))
def aerial_control(front, orig, k):
    car_direction = Vec3(math.cos(orig.yaw) * math.cos(orig.pitch), math.sin(orig.yaw) * math.cos(orig.pitch), math.sin(orig.pitch))
    to_attack = get_aerial_control(dir_convert(front), orig)
    # Roll
    '''
    controls.roll = 1
    '''
    # Controls
    p_c = math.cos(to_attack)
    p_y = -math.sin(to_attack)
    # Pitch & Yaw
    return (p_c * math.cos(orig.roll) + p_y * math.sin(orig.roll)) * clamp(get_angle(front, car_direction) * k, -1, 1), (p_y * math.cos(orig.roll) - p_c * math.sin(orig.roll)) * clamp(get_angle(front, car_direction) * k, -1, 1)
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
'''
Section: Dropshot
'''
# Get the row of a tile based on index
def get_row(index):
    if index == clamp(math.floor(index), 0, 139):
        if index < 70:
            return math.floor(-6.5 + math.sqrt(2 * index + 6.5**2))
        else:
            return math.floor(20.5 - math.sqrt(2 * (140 - index) + 6.5**2))
# Get the index minimum of a tile based on row
def get_index_minimum(row):
    if row < 7:
        return (row**2 + 13 * row) // 2
    else:
        return 161 - (row - 21) * (row - 20) // 2
# Get the position of a tile
def get_pos(index):
    row = get_row(index)
    y = (122 + 576 / math.cos(math.pi / 6) * clamp(abs(6.5 - row) - 0.5, 0, 7)) * sign(row - 6.5)
    x = 768 * 3 - 384 * (abs(row - 6.5) - 6.5) - 768 * (index - get_index_minimum(row))
    return Vec3(x, y, 0)
'''
# Update damage to tiles
def damage_tile(li, pos, power):
    new_li = li
    if abs(pos.y) > 122:
        aff_row = 6.5 + sign(pos.y) * (0.5 + math.floor((abs(pos.y) - 122) / (576 / math.cos(math.pi / 6)) - 122))
        row_min = math.floor(aff_row)
        row_max = math.ceil(aff_row)
        index_min = get_index_minimum(row_min)
        pos_min = get_pos(index_min)
        index_max = get_index_minimum(row_max)
        pos_max = get_pos(index_max)
        if (pos_min - pos).length() < (pos_max - pos).length():
            index = index_min
        else:
            index = index_max
        row = get_row(index)
        new_li[index] = clamp(new_li[index] + 1, 0, 2)
        # Damage multiple tiles
        if 3 >= power >= 2:
            for i in range(row - (power - 1), row + power):
                index_in_row = 
                for l in range():
    return new_li
'''
# Reset tiles after goal
def reset_side(li, team):
    new_li = li
    for i in range(70):
        new_li[i + team * 70] = 0
    return new_li