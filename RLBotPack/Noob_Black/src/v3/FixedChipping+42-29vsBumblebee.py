from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.orientation import Orientation, relative_location
from util.vec import Vec3

import math, time, random

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.prev_jump = False
        self.jump_tick = 0
        # Rotations
        self.prev_frame_nr = 0
        self.prev_rot = [0, 0, 0]
        self.prev_wait = False
        self.just_flipped = -100
        self.prev_touch = [-1, 0]
        self.should_chip = False
        self.prev_double_jump = False
        self.attacking_bot = None
        self.defending_bot = None
        # Bot custom vars
        self.defensive_stance = False

    def initialize_agent(self):
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        begin = time.time()
        self.boost_pad_tracker.update_boost_status(packet)

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        # Taken from the utils but modified for smooth reversing
        def steer_toward_target_absolute(target: Vec3) -> float:
            relative = relative_location(Vec3(my_car.physics.location), Orientation(my_car.physics.rotation), target)
            if get_angle(front_direction, car_velocity) < math.pi / 2:
                angle = math.atan2(relative.y, relative.x)
            else:
                angle = math.atan2(relative.y, relative.x)
                angle = abs(math.pi - angle) * sign(angle, 1)
            return clamp(angle * 5, -1, 1)
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
        
        def point_toward(aerial_front):
            vd_pitch, vd_yaw = aerial_control(aerial_front, car_rotation, 1)
            c_pitch = vd_pitch - math.sqrt(abs(rot_vel[0]) / 6.23) * sign(rot_vel[0]) * math.cos(car_rotation.roll - rot_vel[2] / 120) - math.sqrt(abs(rot_vel[1]) / 6.23) * sign(rot_vel[1]) * math.sin(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch)
            c_yaw = vd_yaw - math.sqrt(abs(rot_vel[1]) / 4.555) * sign(rot_vel[1]) * math.cos(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch) - math.sqrt(abs(rot_vel[0]) / 4.555) * sign(rot_vel[0]) * -math.sin(car_rotation.roll - rot_vel[2] / 120)
            if abs(c_pitch) > abs(c_yaw):
                c_pitch, c_yaw = c_pitch / abs(c_pitch), c_yaw / abs(c_pitch)
            elif abs(c_yaw) > abs(c_pitch):
                c_pitch, c_yaw = c_pitch / abs(c_yaw), c_yaw / abs(c_yaw)
            controls.pitch, controls.yaw = c_pitch, c_yaw
        
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
        
        def new_jump_time(h, double):
            single_time = solve_quadratic(-325.0556640625, 564.9931640625, -11.6591796875, min(h, max_jump_height[0]), -1)
            if single_time >= 24 / 120:
                if single_time >= 25 / 120 and double:
                    return solve_quadratic(-325.0556640625, 564.9931640625 + 292, -11.6591796875 - 292 * 25 / 120, min(h, max_jump_height[1]), -1), 2
                else:
                    return single_time, 1
            else:
                return solve_quadratic(392.2802734375, 272.7626953125, 17.671875, h, 1), 1
        
        def new_max_jump_height(double):
            x = -(564.9931640625 + 292 * bool(double)) / (-325.0556640625 * 2)
            return -325.0556640625 * x**2 + (564.9931640625 + 292 * bool(double)) * x + -11.6591796875 - 292 * 25 / 120 * bool(double)
        
        def get_preds():
            li = [packet.game_ball]
            for i in range(1, 301):
                li.append(find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + i / 60))
            return li
        
        def get_acceleration(v):
            vels = [v]
            dists = [0]

            for i in range(600):
                v = vels[-1]
                boost_used = bool(i / 3.6 < my_car.boost)
                if v <= 1400:
                    vels.append(v + (1600 - 1440 / 1400 * v + 2975 / 3 * boost_used) / 120)
                elif v < 1410:
                    vels.append(v + (22560 - 16 * v + 2975 / 3 * boost_used) / 120)
                else:
                    vels.append(min(v + 2975 / 360 * boost_used, 2300))
                dists.append(dists[-1] + vels[-1] / 120)
            return dists, vels
        
        def get_acceleration_boostless(v):
            vels = [v]
            dists = [0]

            for i in range(600):
                v = vels[-1]
                if v <= 1400:
                    vels.append(v + (1600 - 1440 / 1400 * v) / 120)
                elif v < 1410:
                    vels.append(v + (22560 - 16 * v) / 120)
                else:
                    vels.append(v)
                dists.append(dists[-1] + vels[-1] / 120)
            return dists, vels
        
        def yaw_conversion(p1, p2):
            if abs(p1 - p2) > math.pi:
                return p2 - p1 + math.pi * 2 * sign(p1 - p2)
            else:
                return p2 - p1
        def roll_conversion(p1, p2):
            if abs(p1 - p2) > math.pi / 2:
                return p2 - p1 + math.pi * sign(p1 - p2)
            else:
                return p2 - p1
        
        def air_pos(pos, vel, t):
            return pos + vel * t + Vec3(0, 0, -325) * t**2
        
        def goal_time():
            for i in range(1, 301):
                if abs(ball_states[i].physics.location.y) >= 5235:
                    return i / 60
            return -1
        
        def target_func_flat(pos):
            return Vec3(0, goal_location.y, 0)
        
        def target_func(pos):
            dev = abs(pos.y - goal_location.y)
            y_offset = dev * math.tan(min(dev / 5120, 1) * math.pi / 4)
            return Vec3(0, goal_location.y, y_offset)
        
        def shot_variables_defense(defensive_y = -5020):
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Intersections with lines
            flat_front = right_direction.flat().normalized()
            x_coefficient = flat_front.x
            y_coefficient = flat_front.y
            target_coefficient = car_location.x * x_coefficient + car_location.y * y_coefficient
            first_c = sign(ball_location.x * x_coefficient + ball_location.y * y_coefficient - target_coefficient)
            car_front_intersection = 5
            for i in range(round(max_t * 60) + 1):
                if sign(ball_states[i].physics.location.x * x_coefficient + ball_states[i].physics.location.y * y_coefficient - target_coefficient) != first_c:
                    car_front_intersection = i
                    break
            goal_intersection = 5
            goal_direction = sign(goal_location.y)
            for i in range(round(max_t * 60) + 1):
                if ball_states[i].physics.location.y * goal_direction < defensive_y:
                    goal_intersection = i
                    break
            def hit_d_check(bpos, t, used_d, used_v):
                np = bpos - offset_vec * 134.85
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return used_d[ticks_driving] + used_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_double_check(bpos, t, used_d, used_v):
                np = bpos - offset_vec * 92.75
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), True)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return used_d[ticks_driving] + used_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Get the best prediction to shoot at
            target_t = [[max_t, max_t], [max_t, max_t], car_front_intersection / 60, goal_intersection / 60]
            boosted = [False, False]
            target_f = [[ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]], [ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]], ball_states[car_front_intersection], ball_states[goal_intersection]]
            wait_for_fall = [[-1, -1], [-1, -1]]
            for i in range(round(max_t * 60) + 1):
                t = i / 60
                bp = ball_states[i]
                bpos = Vec3(bp.physics.location)
                offset_vec = Vec3(math.sqrt(0.5) * (bpos.x - car_location.x), math.sqrt(0.5) * goal_direction, 0).normalized()
                if target_t[0][1] == max_t:
                    if boosted[0] == False and hit_d_check(bpos, t, travel_d, travel_v): # Hits
                        if bpos.z - offset_vec.z * 134.85 > max_jump_height[0]:
                            if wait_for_fall[0][0] == -1:
                                wait_for_fall[0][0] = t
                        else:
                            target_t[0][0] = t
                            target_f[0][0] = bp
                            boosted[0] = True
                    if boosted[0] == True and hit_d_check(bpos, t, travel_d_boostless, travel_v_boostless): # Hits
                        if bpos.z - offset_vec.z * 134.85 > max_jump_height[0]:
                            if wait_for_fall[0][1] == -1:
                                wait_for_fall[0][1] = t
                        else:
                            target_t[0][1] = t
                            target_f[0][1] = bp
                if target_t[1][1] == max_t:
                    if boosted[1] == False and hit_double_check(bpos, t, travel_d, travel_v): # Double Jumps
                        if bpos.z - offset_vec.z * 92.75 > max_jump_height[1] + 60:
                            if wait_for_fall[1][0] == -1:
                                wait_for_fall[1][0] = t
                        else:
                            target_t[1][0] = t
                            target_f[1][0] = bp
                            boosted[1] = True
                    if boosted[1] == True and hit_double_check(bpos, t, travel_d_boostless, travel_v_boostless): # Double Jumps
                        if bpos.z - offset_vec.z * 92.75 > max_jump_height[1] + 60:
                            if wait_for_fall[1][1] == -1:
                                wait_for_fall[1][1] = t
                        else:
                            target_t[1][1] = t
                            target_f[1][1] = bp
            return [target_t, target_f, wait_for_fall]
        
        def goalie(li, y = -5020, car_li = None):
            target_t, target_f, wait_for_fall = li[0], li[1], li[2]
            if car_li == None:
                # Get list of cars
                car_li = [[self.index], []]
                for i in range(len(packet.game_cars)):
                    if packet.game_cars[i].name != "":
                        car_li[bool(packet.game_cars[i].team != self.team)].append(i)
            poses = []
            pos_sum = 0
            for i in car_li[1]:
                other_loc = Vec3(packet.game_cars[i].physics.location)
                poses.append([(ball_location - other_loc).flat().normalized(), (other_loc.dist(ball_location) / 500)**0.5])
                pos_sum += poses[-1][1]
            pos_offset = Vec3(0, 0, 0)
            for i in poses:
                pos_offset += i[0] * i[1]
            pos_offset = pos_offset.normalized()
            # In Goal
            if save_deadline >= 0:
                target_ball = Vec3(target_f[3].physics.location)
                tpos = -goal_location + Vec3(target_ball.x, 0, 0)
                controls.steer = steer_toward_target_absolute(tpos)
                controls.throttle = sign(front_direction.x * (tpos.x - car_location.x)) * (1 - 2 * bool(car_velocity.length() * sign(car_velocity.x * (tpos.x - car_location.x)) * target_t[3] > abs(tpos.x - car_location.x)))
                jt, ja = new_jump_time(target_ball.z - 17, True)
                if jt > target_t[3]:
                    controls.jump = my_car.has_wheel_contact == True or abs(packet.game_info.frame_num - self.jump_tick) < 24 or not self.prev_jump
                self.renderer.draw_line_3d(tpos, car_location, self.renderer.blue())
            elif car_location.flat().dist(-goal_location) < 900:
                ball_indent = abs(ball_location.y + goal_location.y)
                tpos = -goal_location + Vec3(clamp((ball_location.x + pos_offset.x * 500 * (ball_indent / 2000 * 0.5**(ball_indent / 2000))) / max(1, ball_location.flat().dist(-goal_location) / 900), -750, 750), 0, 0)
                controls.throttle = sign(front_direction.x * (tpos.x - car_location.x - car_velocity.x * abs(car_velocity.x) / 6000)) * bool(car_velocity.length() > 30 or tpos.flat().dist(car_location.flat()) > 30)
                if car_velocity.length() > 50 or abs(front_direction.y) > 0.1:
                    controls.steer = steer_toward_target_absolute(Vec3(1000 * sign(car_velocity.x, 1), -goal_location.y, 0))
                self.renderer.draw_line_3d(tpos, car_location, self.renderer.green())
            else:
                tpos = -goal_location + Vec3(min(car_location.flat().dist(-goal_location) / 1500, 1) * 800 * sign(car_location.x), 0, 0)
                controls.steer = steer_toward_target(my_car, tpos)
                controls.throttle = 1 - 2 * bool(car_velocity.length()**2 * (1 - 2 * bool(get_angle(front_direction, car_velocity) > math.pi / 2)) / 6000 > car_location.flat().dist(-goal_location) - 50 or car_velocity.length() > 1000 + abs(car_location.y + goal_location.y))
                if my_car.has_wheel_contact == True and abs(controls.steer) <= 0.01 and car_velocity.flat().length() >= 1000 and car_location.flat().dist(tpos.flat()) - 900 >= car_velocity.flat().length() * 1.4 + 500 * 1.5 + car_velocity.flat().length()**2 / 7000:
                    override = self.begin_front_flip(packet)
                if abs(self.just_flipped - packet.game_info.frame_num) > 78 and car_velocity.z < -10:
                    recover(tpos)
                self.renderer.draw_line_3d(tpos, car_location, self.renderer.red())
        
        def shot_variables_2(target):
            def closest_check(bpos, t):
                dt = bpos.flat().dist(car_location.flat())
                if target_t[4] == 0:
                    if dt >= wait_for_fall[4]:
                        wait_for_fall[4] = dt
                    else:
                        target_t[4] = -t
                elif target_t[4] < 0:
                    if dt <= wait_for_fall[4]:
                        wait_for_fall[4] = dt
                        target_t[4] = -t
                    else:
                        target_t[4] = abs(target_t[4])
            def flick_d_check(bpos, t):
                if bpos.z > 130:
                    return False
                dt = bpos.flat().dist(car_location.flat())
                return travel_d[round(t * 120)] >= dt
            '''
            def flick_d_check(bpos, t):
                dt = bpos.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(bpos.z - 130, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - max(jt, 0), 0), 5) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            '''
            def hit_d_check(bpos, t):
                np = bpos - offset_vec * 134.85
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_double_check(bpos, t):
                np = bpos - offset_vec * 92.75
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), True)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def aerial_d_check(bpos, t):
                np = bpos - offset_vec * 92.75
                dt = np.dist(car_location + car_velocity * t + Vec3(0, 0, -325) * air_t + up_direction * jump_vec)
                return dt <= 2975 / 6 * air_t
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Get the best prediction to shoot at
            target_t = [max_t, max_t, max_t, max_t, 0]
            target_f = [ball_states[round(max_t * 60)], ball_states[round(max_t * 60)], ball_states[round(max_t * 60)], ball_states[round(max_t * 60)], ball_states[0]]
            wait_for_fall = [-1, -1, -1, -1, 0]
            air_t = 0
            jump_vec = (292 * bool(not my_car.double_jumped) + 146 * bool(not my_car.jumped) + 146 / 24 * max(24 - abs(packet.game_info.frame_num - self.jump_tick), 0))
            for i in range(round(max_t * 60) + 1):
                t = i / 60
                bp = ball_states[i]
                bpos = Vec3(bp.physics.location)
                target_p = target(bpos)
                offset_vec = (target_p - bpos).normalized()
                if target_t[0] == max_t and flick_d_check(bpos, t): # Flicks
                    if bpos.z > 130:
                        if wait_for_fall[0] == -1:
                            wait_for_fall[0] = t
                    else:
                        target_t[0] = t
                        target_f[0] = bp
                if target_t[1] == max_t and hit_d_check(bpos, t): # Hits
                    if bpos.z - offset_vec.z * 134.85 > max_jump_height[0]:
                        if wait_for_fall[1] == -1:
                            wait_for_fall[1] = t
                    else:
                        target_t[1] = t
                        target_f[1] = bp
                if target_t[2] == max_t and hit_double_check(bpos, t): # Double Jumps
                    if bpos.z - offset_vec.z * 92.75 > max_jump_height[1] + 60:
                        if wait_for_fall[2] == -1:
                            wait_for_fall[2] = t
                    else:
                        target_t[2] = t
                        target_f[2] = bp
                if target_t[3] == max_t: # Aerials
                    if aerial_d_check(bpos, t):
                        target_t[3] = t
                        target_f[3] = bp
                    else:
                        air_t += (2 * i + 1) / 3600
                if target_t[4] <= 0: # Closest shot
                    closest_check(bpos, t)
            wait_for_fall[0] = 1
            return [target_t, target_f, wait_for_fall]
        
        def shot_variables_line(target, p1, p2):
            def hit_d_check(bpos, td, tv, t):
                np = bpos - offset_vec * 134.85
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return td[ticks_driving] + tv[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_double_check(bpos, td, tv, t):
                np = bpos - offset_vec * 92.75
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), True)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return td[ticks_driving] + tv[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def cross_line_check(bpos, l):
                np = bpos - offset_vec * l
                d = (np - p1).flat().length() * math.cos(get_angle((np - p1).flat(), line_vec))
                return d
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Setup
            line_vec = Vec3(p2.y - p1.y, p1.x - p2.x, 0).flat()
            single_d = cross_line_check(ball_location, 134.85)
            double_d = cross_line_check(ball_location, 92.75)
            # Get the best prediction to shoot at
            target_t = [[max_t, max_t], [max_t, max_t], max_t, max_t]
            time_boost = [False, False]
            target_f = [[ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]], [ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]], ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]]
            wait_for_fall = [-1, -1, -1]
            for i in range(round(max_t * 60) + 1):
                t = i / 60
                bp = ball_states[i]
                bpos = Vec3(bp.physics.location)
                target_p = target(bpos)
                offset_vec = (target_p - bpos).normalized()
                if target_t[2] == max_t:
                    d = cross_line_check(bpos, 134.85)
                    if sign(d) != sign(single_d):
                        target_t[2] = t
                        target_f[2] = bp
                if target_t[3] == max_t:
                    d = cross_line_check(bpos, 92.75)
                    if sign(d) != sign(double_d):
                        target_t[3] = t
                        target_f[3] = bp

        def shoot_ball(target, li, other_cars, flick = False, double_jump = False, aerial = False, param = ""):
            target_t, target_f, wait_for_fall = li[0], li[1], li[2]
            mode_index = 3 * bool(aerial) + (1 + bool(double_jump)) * bool(not flick and not aerial)
            grounded_mode_index = (1 + bool(double_jump)) * bool(not flick)
            # Drive
            will_aerial = aerial == True and my_car.boost / 100 * 3 >= target_t[3] + 0.1 * bool(my_car.has_wheel_contact) and wait_for_fall[grounded_mode_index] >= 0
            if will_aerial:
                og_bpos = Vec3(target_f[3].physics.location)
                bpos = og_bpos - (target(og_bpos) - og_bpos).rescale(92.75)
                bvel = Vec3(target_f[3].physics.velocity)
            elif flick == False:
                if double_jump == True:
                    og_bpos = Vec3(target_f[2].physics.location)
                    bpos = og_bpos - (target(og_bpos) - og_bpos).rescale(92.75)
                    bvel = Vec3(target_f[2].physics.velocity)
                else:
                    og_bpos = Vec3(target_f[1].physics.location)
                    bpos = og_bpos - (target(og_bpos) - og_bpos).rescale(134.85)
                    bvel = Vec3(target_f[1].physics.velocity)
            else:
                og_bpos = Vec3(target_f[0].physics.location)
                bpos = Vec3(target_f[0].physics.location)
                bvel = Vec3(target_f[0].physics.velocity)
            # Get whether to boost for a double jump
            d_to_travel = bpos.flat().dist(car_location.flat())
            tjt, tja = new_jump_time(max(bpos.z - 130 * bool(flick == True), 0), True)
            ticks_charging = round(target_t[grounded_mode_index] * 120)
            ticks_driving = round(min(max(target_t[grounded_mode_index] - tjt, 0), 5) * 120)
            should_boost = travel_d_boostless[ticks_driving] + travel_v_boostless[ticks_driving] * (ticks_charging - ticks_driving) / 120 < d_to_travel or wait_for_fall[grounded_mode_index] < 0
            # 
            controls.throttle = 1 - 2 * bool(wait_for_fall[grounded_mode_index] >= 0 and car_velocity.flat().length() * target_t[grounded_mode_index] > car_location.flat().dist(bpos.flat()) and (car_velocity.length() == 0 or car_velocity.ang_to(front_direction) < math.pi / 2))
            controls.boost = my_car.has_wheel_contact == True and controls.throttle == 1 and car_velocity.length() < 2299 and should_boost == True and (wait_for_fall[grounded_mode_index] < 0 or travel_d[2] + travel_v[2] * (target_t[grounded_mode_index] - 1 / 60) < d_to_travel)
            controls.steer = steer_toward_target(my_car, bpos.flat())
            # Powerslide in some situations
            if get_angle(front_direction.flat(), (bpos - car_location).flat()) > math.pi / 4 and ((bpos - car_location).flat().length() <= 1000 + car_velocity.flat().length() or car_location.y * sign(goal_location.y) < -5120):
                if get_angle(bvel.flat(), (bpos - car_location).flat()) <= math.pi / 2:
                    controls.handbrake = get_angle(car_velocity, front_direction) <= math.pi / 4 and Vec3(my_car.physics.angular_velocity).length() > min(1.5, car_velocity.length() / 700)
                    controls.boost = False
            # Flip in some situations
            flip_vel = min(car_velocity.flat().length() + 500, 2300)
            current_d = (ball_location.flat() + ball_velocity.flat() * 0.1).dist(car_location.flat()) - car_velocity.flat().length() / 10
            one_sec_d = (ball_location.flat() + ball_velocity.flat() * 1.1).dist(car_location.flat()) - car_velocity.flat().length() / 10 - flip_vel
            t = current_d * safe_div(current_d - one_sec_d)
            tick_t = clamp(round(t * 60), 0, 300)
            flip_ball = Vec3(ball_states[tick_t].physics.location)
            flip_ballv = Vec3(ball_states[tick_t].physics.velocity)
            if flip_ball.flat().dist(ball_location.flat() + ball_velocity.flat() * tick_t / 60) <= max((ball_velocity.flat().length() * tick_t / 60) * math.tan(math.pi / 20), travel_d[clamp(tick_t * 2 - round(tjt * 120), 0, 600)] / 25):
                test_jt, test_ja = new_jump_time(max(flip_ball.z + flip_ballv.z**2 / 1300, 0), True)
                if t >= 1.4 + test_jt:
                    controls.steer = steer_toward_target(my_car, ball_location.flat() + ball_velocity.flat() * t)
                    if my_car.has_wheel_contact == True and abs(controls.steer) <= 0.1 and car_velocity.flat().length() >= 1000 + 1400 * bool(my_car.boost > 0):
                        override = self.begin_front_flip(packet)
            # In goal safety
            if bpos.y * sign(goal_location.y) <= -5030 and abs(bpos.x) >= 1000 and abs(car_location.x) < 900:
                rel_pos = Vec3(sign(bpos.x) * (450 + car_location.x * sign(bpos.x) / 2), sign(-goal_location.y) * 5070, 0)
                if (rel_pos - car_location).flat().rescale((bpos - car_location).flat().length()).y * sign(goal_location.y) > bpos.y * sign(goal_location.y):
                    controls.steer = steer_toward_target(my_car, rel_pos)
                    controls.handbrake = get_angle(car_velocity, front_direction) <= math.pi / 4 and Vec3(my_car.physics.angular_velocity).length() > min(1.5, car_velocity.length() / 700) and get_angle(front_direction, rel_pos - car_location) > math.pi / 4 and get_angle(rel_pos - car_location, front_direction) < get_angle(rel_pos - car_location, prev_front)
            # Jumping
            if will_aerial:
                offset = bpos - (car_location + car_velocity * target_t[3] + Vec3(0, 0, -325) * target_t[3]**2) + up_direction * 292 * bool(not my_car.double_jumped)
                if my_car.has_wheel_contact == False:
                    if my_car.boost / 100 * 3 >= target_t[3]:
                        point_toward(offset)
                        controls.boost = front_direction.ang_to(offset) < math.pi / 4
                        controls.throttle = 1
                        controls.jump = my_car.double_jumped == False and (abs(packet.game_info.frame_num - self.jump_tick) < 24 or self.prev_jump == False)
                        target_roof_dir = (bpos - car_location)
                        controls.roll = sign(math.pi / 2 - get_angle(target_roof_dir, right_direction))
                        if my_car.jumped == True and controls.jump == True and self.prev_jump == False:
                            controls.pitch, controls.yaw, controls.roll = 0, 0, 0
                    else:
                        recover(bpos)
                else:
                    if steer_toward_target(my_car, bpos) <= 0.2:
                        controls.jump = True
                    point_toward(offset)
            elif flick == True:
                if abs(self.just_flipped - packet.game_info.frame_num) > 78 and car_velocity.z < -10:
                    recover(bpos)
                jt, ja = new_jump_time(max(bpos.z - 130, 0), False)
                if (round((target_t[0] - jt) * 120) <= 0 and my_car.has_wheel_contact == True) or (my_car.has_wheel_contact == False and self.prev_jump == True) or param == "Flick":
                    controls.jump = True
                if my_car.has_wheel_contact == False:
                    if (ball_location.z - car_location.z - 130) <= (car_velocity.z - ball_velocity.z) / (30 * (1 + bool(self.prev_jump == False))) and car_location.flat().dist(ball_location.flat()) <= 92.75:
                        controls.jump = not self.prev_jump
                        if controls.jump == True:
                            controls.yaw = random.randint(-1, 1)
                            controls.pitch = random.randint(-1, 1)
            elif double_jump == True:
                # Adjust target for faster shots
                if bvel.flat().dist(car_velocity.flat()) > 2000:
                    bpos = Vec3(bpos.x, bpos.y, og_bpos.z + (bpos.z - og_bpos.z) * 2000 / bvel.flat().dist(car_velocity.flat()))
                # Recovery
                if abs(self.just_flipped - packet.game_info.frame_num) > 78 and car_velocity.z < -10:
                    recover(bpos)
                # Decide whether to chip
                if (og_bpos.z <= 110 and bvel.z <= 100 and packet.game_info.is_kickoff_pause == False):
                    self.should_chip = True
                elif abs(controls.steer) < 0.5:
                    self.should_chip = False
                # Jumping
                jt, ja = new_jump_time(max(bpos.z, 0), True)
                if my_car.has_wheel_contact == True:
                    controls.jump = round((target_t[2] - jt) * 120) <= 0 and get_angle(front_direction.flat(), (bpos - car_location).flat()) <= math.pi / 2 and self.should_chip == False
                elif [packet.game_ball.latest_touch.player_index, packet.game_ball.latest_touch.time_seconds] == self.prev_touch or packet.game_ball.latest_touch.player_index != self.index:
                    if abs(packet.game_info.frame_num - self.jump_tick) < 24:
                        controls.jump = True
                    else:
                        controls.jump = not self.prev_jump
                        if controls.jump == True and self.prev_jump == False and my_car.double_jumped == False:
                            controls.pitch, controls.yaw, controls.roll = 0, 0, 0
                if my_car.double_jumped == True and car_velocity.z > 0:
                    if self.prev_wait == True:
                        point_toward(Vec3(0, 0, 1))
                        target_roof_dir = (ball_location - car_location).flat()
                        controls.roll = sign(math.pi / 2 - get_angle(target_roof_dir, right_direction))
                    else:
                        point_toward((ball_location - car_location).flat())
            else:
                # Adjust target for faster shots
                if bvel.flat().dist(car_velocity.flat()) > 2000:
                    bpos = Vec3(bpos.x, bpos.y, og_bpos.z + (bpos.z - og_bpos.z) * 2000 / bvel.flat().dist(car_velocity.flat()))
                # Recovery
                if abs(self.just_flipped - packet.game_info.frame_num) > 78 and car_velocity.z < -10:
                    recover(bpos)
                # Decide whether to chip
                if (og_bpos.z <= 110 and bvel.z <= 100 and packet.game_info.is_kickoff_pause == False):
                    self.should_chip = True
                elif abs(controls.steer) < 0.5:
                    self.should_chip = False
                # Jumping
                jt, ja = new_jump_time(max(bpos.z, 0), False)
                if ((round((target_t[1] - jt) * 120) <= 0 and my_car.has_wheel_contact == True and get_angle(front_direction.flat(), (bpos - car_location).flat()) <= math.pi / 2) or (my_car.has_wheel_contact == False and self.prev_jump == True) or ((car_location + car_velocity / 20 + Vec3(0, 0, -325) / 400).dist(Vec3(ball_states[3].physics.location)) <= 150 and my_car.has_wheel_contact == True)) and self.should_chip == False:
                    controls.jump = True
                if abs(packet.game_info.frame_num - self.jump_tick) >= 24 and abs(self.just_flipped - packet.game_info.frame_num) > 78:
                    point_toward((ball_location - car_location).flat())
                if my_car.has_wheel_contact == False:
                    if (car_location + car_velocity / 60 + Vec3(0, 0, -325) / 3600).dist(Vec3(ball_states[1].physics.location)) <= 150 or packet.game_ball.latest_touch.player_index == self.index != self.prev_touch[0]:
                        controls.jump = not self.prev_jump
                        if controls.jump == True:
                            controls.pitch = -math.floor(math.cos(front_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
                            controls.yaw = math.floor(math.cos(right_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
                    elif (car_location + car_velocity / 30 + Vec3(0, 0, -325) / 900).dist(Vec3(ball_states[2].physics.location)) <= 150:
                        controls.jump = False
            if will_aerial == False and flick == False:
                if my_car.has_wheel_contact == False and packet.game_ball.latest_touch.player_index == self.index != self.prev_touch[0] and my_car.double_jumped == False:
                    controls.jump = not self.prev_jump
                    if controls.jump == True:
                        controls.pitch = -math.floor(math.cos(front_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
                        controls.yaw = math.floor(math.cos(right_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
            
            if my_car.has_wheel_contact == True:
                self.prev_wait = bpos.z > max_jump_height[1]
                if packet.game_info.is_kickoff_pause == True:
                    if car_velocity.length() > 800 and car_location.dist(ball_location) > 2500 and my_car.boost > 10 and get_angle(front_direction.flat(), (ball_location - car_location).flat()) < 0.1:
                        self.speed_flip(packet, sign(car_location.x * goal_location.y))
            self.renderer.draw_line_3d(bpos, car_location, self.renderer.green())
            self.renderer.draw_line_3d(bpos, og_bpos, self.renderer.red())
            controls.use_item = True

        def defense(goalie = False, fast = False):
            # Get potential boost pads
            best_pad = None
            large_available = False
            if my_car.boost < 100 and fast == False:
                best_score = math.inf
                for i in range(len(self.get_field_info().boost_pads)):
                    pad = self.get_field_info().boost_pads[i]
                    best_score = math.inf
                    if (abs(pad.location.x) > 3000 or abs(pad.location.y) > 4000) and Vec3(pad.location).dist(-goal_location) < car_location.dist(-goal_location) and sign(pad.location.x) == sign(car_location.x):
                        if packet.game_boosts[i].is_active == True or packet.game_boosts[i].timer <= (Vec3(pad.location) - car_location).length() / 2300:
                            score = Vec3(pad.location).dist(car_location) + Vec3(pad.location).dist(-goal_location)
                            if pad.is_full_boost == True:
                                large_available = True
                            if large_available == True and (best_pad != None and best_pad.is_full_boost == False or score < best_score) or (large_available == False or score < best_score):
                                best_pad = pad
                                best_score = score

            if best_pad != None:
                tl = Vec3(best_pad.location)
            else:
                if goalie == True:
                    tl = Vec3(0, -goal_location.y - sign(goal_location.y) * 150, 0)
                else:
                    tl = Vec3(sign(car_location.x) * 900, -goal_location.rescale(5050).y, 0)
            # General controls
            if car_location.dist(-goal_location) <= 1500:
                if car_velocity.length() <= 100 and -5320 + 200 * bool(goalie == False) > car_location.y * sign(goal_location.y) and get_angle(front_direction, tl - car_location) > math.pi / 4:
                    controls.handbrake = True
                    controls.throttle = -sign(math.pi / 2 - get_angle(front_direction, car_velocity))
                    controls.steer = steer_toward_target(my_car, tl) * controls.throttle
                elif car_velocity.length() <= 100 and -5320 + 200 * bool(goalie == False) <= car_location.y * sign(goal_location.y) <= -5120 + 100 * bool(goalie == False) and get_angle(front_direction, ball_location - car_location) >= 0.2:
                    controls.handbrake = True
                    controls.throttle = -sign(math.pi / 2 - get_angle(front_direction, car_velocity))
                    if goalie == True:
                        if (ball_location.flat() - Vec3(clamp(ball_location.x, -900, 900), 0, 0) + goal_location).ang_to(goal_location) <= math.pi / 3:
                            controls.steer = steer_toward_target(my_car, ball_location) * controls.throttle
                        else:
                            controls.steer = steer_toward_target(my_car, -goal_location + Vec3(ball_location.x, sign(ball_location.y + goal_location.y) / math.tan(math.pi / 3) * (abs(ball_location.x) - 900), 0)) * controls.throttle
                    else:
                        controls.steer = steer_toward_target(my_car, Vec3(0, car_location.y, 0)) * controls.throttle
                else:
                    controls.throttle = sign(-sign(math.pi / 2 - get_angle(car_velocity, front_direction)) * car_velocity.length()**2 / 6000 + sign(math.pi / 2 - get_angle(tl - car_location, front_direction)) * tl.dist(car_location), 1)
                    controls.steer = steer_toward_target(my_car, tl)
                    # Prevent understeer to the goal
                    if goalie == False and car_velocity.flat().length() > 100 and get_angle((Vec3(sign(car_location.x) * 900, -goal_location.rescale(5050).y, 0) - car_location).flat(), car_velocity.flat()) > min(math.asin(min(25000 / 11 * (tl - car_location).flat().length(), 1)) * 2, 1) < get_angle((Vec3(-sign(car_location.x) * 900, -goal_location.rescale(5050).y, 0) - car_location).flat(), car_velocity.flat()):
                        controls.throttle = -sign(math.pi / 2 - get_angle(car_velocity, front_direction))
            else:
                controls.throttle = 1
                controls.handbrake = car_velocity.length() < 1000 and get_angle(car_velocity, front_direction) <= math.pi / 4 and get_angle(front_direction, tl - car_location) > math.pi / 4 and Vec3(my_car.physics.angular_velocity).length() >= min(car_velocity.length() / 500, 2) and get_angle(tl - car_location, front_direction) < get_angle(tl - car_location, prev_front)
                controls.boost = best_pad != None and best_pad.is_full_boost == True and my_car.has_wheel_contact == True != controls.handbrake
                if my_car.has_wheel_contact == True and abs(car_rotation.roll) > 0.2:
                    tl = car_location.flat()
                controls.steer = steer_toward_target(my_car, tl)
                if my_car.has_wheel_contact == True and abs(controls.steer) <= 0.01 and car_velocity.flat().length() >= 1000 and (car_location.flat().dist(tl.flat()) >= car_velocity.flat().length() * 1.4 + 500 * 1.5 + car_velocity.flat().length()**2 / 7000 or (best_pad != None and best_pad.is_full_boost == True and abs(car_location.y + front_direction.y * (car_velocity.flat().length() * 1.4 + 500 * 1.5 + car_velocity.flat().length()**2 / 7000)) < 5000)):
                    override = self.begin_front_flip(packet)
            if abs(self.just_flipped - packet.game_info.frame_num) > 78 and car_velocity.z < -10:
                recover(tl)
            self.renderer.draw_line_3d(tl, car_location, self.renderer.red())
        
        def prepare_for_attack(side = 0):
            tpos = Vec3(4000 * side, 0, 0)
            tpos = -goal_location + (tpos + goal_location).rescale(tpos.dist(-goal_location) / 5120 * max(min(ball_location.y * goal_location.y + 1000, 5120), 1000))
            if car_location.flat().dist(tpos) <= 100:
                controls.throttle = sign(-sign(math.pi / 2 - get_angle(car_velocity, front_direction)) * car_velocity.length()**2 / 6000 + sign(math.pi / 2 - get_angle(tpos - car_location, front_direction)) * tpos.dist(car_location.flat()), 1)
            else:
                controls.throttle = sign(tpos.dist(car_location.flat()) - car_velocity.length()**2 / 6000)
            controls.handbrake = get_angle(car_velocity, front_direction) <= math.pi / 4 and get_angle(front_direction, tpos - car_location.flat()) > math.pi / 4 and Vec3(my_car.physics.angular_velocity).length() >= min(car_velocity.length() / 500, 2) and get_angle(tpos - car_location.flat(), front_direction) < get_angle(tpos - car_location.flat(), prev_front)
            controls.steer = steer_toward_target(my_car, tpos)
        
        def recover(tl):
            nb = next_bounce(car_location, car_velocity, 17, 650)
            npos = car_location + car_velocity * nb + Vec3(0, 0, -325) * nb**2
            if car_velocity.flat().length() > 0 and get_angle(car_velocity.flat(), (tl - npos).flat()) > math.pi / 2:
                point_toward(Vec3(tl.y - npos.y, npos.x - tl.x, 0))
            else:
                point_toward((tl - npos).flat())
            controls.roll = clamp(-my_car.physics.rotation.roll - rot_vel[2] * abs(rot_vel[2]) / 76.68, -0.1, 0.1) * 10
            
        def general_strategy():
            # Get list of cars
            other_cars = [[self.index], []]
            for i in range(len(packet.game_cars)):
                if packet.game_cars[i].name != "":
                    other_cars[bool(packet.game_cars[i].team != self.team)].append(i)
            # Team positioning
            # Strategy variables
            nb = next_bounce(ball_location, ball_velocity, 92.75, 650)
            nb2 = next_bounce(ball_location, -ball_velocity, 92.75, 650)
            nb3 = next_bounce(ball_location, ball_velocity, max_jump_height[1], 650)
            nb31 = next_bounce(ball_location, Vec3(0, 0, ball_velocity.z), max_jump_height[1], 650)
            air_nb = air_pos(ball_location, ball_velocity, nb)
            air_nb2 = air_pos(ball_location, -ball_velocity, nb2)
            air_nb3 = air_pos(ball_location, ball_velocity, nb3)
            # The strategy
            closest_to_ball = [None, math.inf, False]
            furthest_back = [None, math.inf, False]
            if (abs(ball_location.y + goal_location.y) <= 1000 and abs(ball_location.x) >= 900) and save_deadline < 0: # Side wall clears
                for i in other_cars[0]:
                    if packet.game_cars[i].is_demolished == False:
                        cpos = Vec3(packet.game_cars[i].physics.location)
                        furthest_score = min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)
                        front = car_dir(packet.game_cars[i].physics.rotation.pitch, packet.game_cars[i].physics.rotation.yaw)
                        closest_score = cpos.dist(ball_location) + 5000 * bool(cpos.y * sign(goal_location.y) <= -5050 and abs(cpos.x) <= 900 and front.y * sign(goal_location.y) < 0)
                        biggest_dependency = ball_location.x * sign(ball_location.x) >= cpos.x * sign(ball_location.x)
                        if furthest_score < furthest_back[1]:
                            furthest_back = [i, furthest_score]
                        if (closest_score <= closest_to_ball[1] and bool(biggest_dependency) >= closest_to_ball[2]) or bool(biggest_dependency) > closest_to_ball[2]:
                            closest_to_ball = [i, closest_score, bool(biggest_dependency)]
            elif ((abs(air_nb.y + goal_location.y) <= 100 and air_nb.z > 0) or (abs(air_nb2.y + goal_location.y) <= 100 and air_nb2.z > 0)) and save_deadline < 0: # Backwall bounces
                if abs(air_nb.y - goal_location.y) < abs(air_nb2.y - goal_location.y):
                    bpos = air_nb
                else:
                    bpos = air_nb2
                for i in other_cars[0]:
                    if packet.game_cars[i].is_demolished == False:
                        cpos = Vec3(packet.game_cars[i].physics.location)
                        furthest_score = min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)
                        front = car_dir(packet.game_cars[i].physics.rotation.pitch, packet.game_cars[i].physics.rotation.yaw)
                        closest_score = cpos.dist(ball_location) + 5000 * bool(cpos.y * sign(goal_location.y) <= -5050 and abs(cpos.x) <= 900 and front.y * sign(goal_location.y) < 0)
                        biggest_dependency = abs(cpos.y - goal_location.y) + abs(cpos.x - bpos.x) / 5 > abs(bpos.y - goal_location.y)
                        if furthest_score < furthest_back[1]:
                            furthest_back = [i, furthest_score]
                        if (closest_score <= closest_to_ball[1] and bool(biggest_dependency) >= closest_to_ball[2]) or bool(biggest_dependency) > closest_to_ball[2]:
                            closest_to_ball = [i, closest_score, bool(biggest_dependency)]
            else:
                ball_dependency = abs(ball_location.y - goal_location.y)
                if air_nb3.y * goal_location.y > ball_location.y * goal_location.y and nb3 == nb31 and air_nb3.z < 600:
                    ball_dependency = abs(air_nb3.y - goal_location.y)
                for i in other_cars[0]:
                    if packet.game_cars[i].is_demolished == False:
                        cpos = Vec3(packet.game_cars[i].physics.location)
                        furthest_score = min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)
                        front = car_dir(packet.game_cars[i].physics.rotation.pitch, packet.game_cars[i].physics.rotation.yaw)
                        closest_score = cpos.dist(ball_location) + 5000 * bool((math.sin(packet.game_cars[i].physics.rotation.yaw) * goal_location.y < 0 or (cpos.z <= 200 and packet.game_cars[i].double_jumped == True and packet.game_cars[i].physics.velocity.z < 10 and packet.game_cars[i].physics.velocity.y * sign(goal_location.y) < 0)) or cpos.flat().dist(Vec3(sign(cpos.x, 1) * 900, -goal_location.y / 5120 * 5050, 0)) <= 100 or (cpos.y * sign(goal_location.y) <= -5050 and abs(cpos.x) <= 900 and front.y * sign(goal_location.y) < 0))
                        biggest_dependency = abs(cpos.y - goal_location.y) + abs(cpos.x - ball_location.x) / 5 * bool(save_deadline >= 0) > ball_dependency
                        if furthest_score < furthest_back[1]:
                            furthest_back = [i, furthest_score]
                        if (closest_score <= closest_to_ball[1] and bool(biggest_dependency) >= closest_to_ball[2]) or bool(biggest_dependency) > closest_to_ball[2]:
                            closest_to_ball = [i, closest_score, bool(biggest_dependency)]
            if closest_to_ball[0] == self.index:
                if packet.game_info.is_kickoff_pause == True:
                    tf = target_func_flat
                else:
                    tf = target_func
                li = shot_variables_2(tf)
                shoot_ball(tf, li, other_cars, double_jump = li[0][2] < li[0][1] and packet.game_info.is_kickoff_pause == False, aerial = True) # target_t, target_f, wait_for_fall
                self.renderer.draw_string_3d(car_location, 1, 1, "Shoot", self.renderer.green())
            elif furthest_back[0] == self.index:
                defense(True, abs(car_location.y + goal_location.y) > 1000)
                self.should_chip = False
                self.renderer.draw_string_3d(car_location, 1, 1, "Goalie", self.renderer.red())
            else:
                if self.defensive_stance == False and ball_location.y * sign(goal_location.y) > 0 and car_location.y * sign(goal_location.y) <= 50 and (sign(front_direction.y * goal_location.y) > 0 or car_location.y * sign(goal_location.y) < -4120):
                    nearest_opponent = None
                    nearest_dist = math.inf
                    for i in other_cars[1]:
                        cpos = Vec3(packet.game_cars[i].physics.location)
                        d = cpos.dist(ball_location)
                        if d < nearest_dist:
                            nearest_dist = d
                            nearest_opponent = packet.game_cars[i]
                    if nearest_opponent != None:
                        prepare_for_attack(sign(ball_location.x - nearest_opponent.physics.location.x) * 0.5)
                    else:
                        prepare_for_attack()
                else:
                    defense(False, False)
                self.should_chip = False
                self.renderer.draw_string_3d(car_location, 1, 1, "Side", self.renderer.yellow())

        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        car_rotation = my_car.physics.rotation
        rot_vel = [(car_rotation.pitch - self.prev_rot[0]) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1), yaw_conversion(self.prev_rot[1], car_rotation.yaw) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1) * math.cos(car_rotation.pitch), roll_conversion(self.prev_rot[2], car_rotation.roll) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1)]
        front_direction = car_dir(car_rotation.pitch, car_rotation.yaw)
        prev_front = car_dir(self.prev_rot[0], self.prev_rot[1])
        right_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll + math.pi / 2)
        up_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll)
        max_jump_height = [new_max_jump_height(False), new_max_jump_height(True)]
        travel_d, travel_v = get_acceleration(car_velocity.flat().length())
        travel_d_boostless, travel_v_boostless = get_acceleration_boostless(car_velocity.flat().length())
        goal_location = Vec3(0, 5120 * (1 - 2 * bool(self.team == 1)), 0)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        ball_prediction = self.get_ball_prediction_struct()
        ball_states = get_preds()
        if packet.game_info.is_round_active == True:
            save_deadline = goal_time()
        else:
            save_deadline = 0
        override = None

        # ball_study = pred_analysis()
        controls = SimpleControllerState()
        # shoot_ball(goal_location, False, aerial = True)
        if packet.game_info.is_round_active == True:
            general_strategy()
        # self.renderer.draw_string_3d(car_location, 1, 1, str(abs(self.just_flipped - packet.game_info.frame_num)), self.renderer.red())

        if controls.jump == True and self.prev_jump == False and my_car.has_wheel_contact == True:
            self.jump_tick = packet.game_info.frame_num
            self.just_flipped = -10000
            self.prev_touch = [packet.game_ball.latest_touch.player_index, packet.game_ball.latest_touch.time_seconds]
        if my_car.double_jumped == False and my_car.jumped == True and controls.jump == True and self.prev_jump == False and not (controls.yaw == controls.pitch == controls.roll == 0):
            self.just_flipped = packet.game_info.frame_num

        self.prev_jump = controls.jump
        self.prev_frame_nr = packet.game_info.frame_num
        self.prev_rot = [car_rotation.pitch, car_rotation.yaw, car_rotation.roll]

        if override:
            return override
        else:
            return controls

    def begin_front_flip(self, packet):
        # self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        self.active_sequence = Sequence([
            ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.02, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.65, controls=SimpleControllerState(jump=True, pitch=-1)),
        ])

        return self.active_sequence.tick(packet)

    def speed_flip(self, packet, dir):

        self.active_sequence = Sequence([
            ControlStep(duration=5/60, controls=SimpleControllerState(steer = -dir, boost = True)),
            ControlStep(duration=1/60, controls=SimpleControllerState(jump = True, boost = True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump = False, boost = True)),
            ControlStep(duration=1/60, controls=SimpleControllerState(yaw = dir, jump = True, pitch = -1, boost = True)),
            ControlStep(duration=0.6, controls=SimpleControllerState(pitch = 1, boost = True)),
            ControlStep(duration=0.2, controls=SimpleControllerState(yaw = dir, roll = dir, boost = True)),
        ])

        return self.active_sequence.tick(packet)