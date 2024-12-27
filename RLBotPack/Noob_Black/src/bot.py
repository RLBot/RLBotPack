from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

import math, time

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.prev_jump = False
        self.jump_tick = 0
        self.prev_frame_nr = 0
        self.prev_rot = [0, 0, 0]
        self.prev_wait = False
        self.current_attacker = -1

    def initialize_agent(self):
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        begin = time.time()
        self.boost_pad_tracker.update_boost_status(packet)

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
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
            if p1 * p2 != Vec3(0, 0, 0):
                return p1.ang_to(p2)
            else:
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
        
        def target_func(pos):
            y_offset = abs(pos.y - goal_location.y) * math.tan(min(abs(pos.y - goal_location.y) / 5120, 1) * math.pi / 4)
            return Vec3(0, goal_location.y, y_offset)
        
        def shot_variables(target):
            def flick_d_check(bpos, t):
                dt = bpos.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(bpos.z - 130, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - max(jt, 0), 0), 600) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_d_check(bpos, t):
                np = bpos - (target_p - bpos).rescale(134.85)
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), False)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 600) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_double_check(bpos, t):
                np = bpos - (target_p - bpos).rescale(92.75)
                dt = np.flat().dist(car_location.flat())
                jt, ja = new_jump_time(max(np.z, 0), True)
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 600) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def aerial_d_check(bpos, t):
                np = bpos - (target_p - bpos).rescale(92.75)
                dt = np.dist(car_location + car_velocity * t + Vec3(0, 0, -325) * t**2 + up_direction * (292 * bool(not my_car.double_jumped) + 146 * bool(not my_car.jumped) + 146 / 24 * max(24 - abs(packet.game_info.frame_num - self.jump_tick), 0)))
                return dt <= 2975 / 6 * t**2
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Get the best prediction to shoot at
            target_t = [max_t, max_t, max_t, max_t]
            target_f = [ball_states[300], ball_states[300], ball_states[300], ball_states[300]]
            wait_for_fall = [-1, -1, -1, -1]
            for i in range(round(max_t * 60) + 1):
                t = i / 60
                bp = ball_states[i]
                bpos = Vec3(bp.physics.location)
                target_p = target(bpos)
                if target_t[0] == max_t and flick_d_check(bpos, t): # Flicks
                    if bpos.z - 130 > max_jump_height[0]:
                        if wait_for_fall[0] == -1:
                            wait_for_fall[0] = t
                    else:
                        target_t[0] = t
                        target_f[0] = bp
                if target_t[1] == max_t and hit_d_check(bpos, t): # Hits
                    if (bpos - (target_p - bpos).rescale(134.85)).z > max_jump_height[0]:
                        if wait_for_fall[1] == -1:
                            wait_for_fall[1] = t
                    else:
                        target_t[1] = t
                        target_f[1] = bp
                if target_t[2] == max_t and hit_double_check(bpos, t): # Double Jumps
                    if (bpos - (target_p - bpos).rescale(92.75)).z > max_jump_height[1] + 152.75:
                        if wait_for_fall[2] == -1:
                            wait_for_fall[2] = t
                    else:
                        target_t[2] = t
                        target_f[2] = bp
                if target_t[3] == max_t and aerial_d_check(bpos, t): # Aerials
                    target_t[3] = t
                    target_f[3] = bp
                if target_t[0] < max_t and target_t[1] < max_t and target_t[2] < max_t and target_t[3] < max_t:
                    break
            return [target_t, target_f, wait_for_fall]

        def shoot_ball(target, li, flick = False, safe = False, double_jump = False, use_boost = False, aerial = False):
            target_t, target_f, wait_for_fall = li[0], li[1], li[2]
            # Drive
            if aerial == True and my_car.boost / 100 * 3 >= target_t[3] + 0.1 * bool(my_car.has_wheel_contact) and wait_for_fall[(1 + bool(double_jump)) * bool(not flick)] >= 0:
                bpos = Vec3(target_f[3].physics.location) - (target(Vec3(target_f[3].physics.location)) - Vec3(target_f[3].physics.location)).rescale(92.75)
            elif flick == False:
                if double_jump == True:
                    bpos = Vec3(target_f[2].physics.location) - (target(Vec3(target_f[2].physics.location)) - Vec3(target_f[2].physics.location)).rescale(92.75)
                else:
                    bpos = Vec3(target_f[1].physics.location) - (target(Vec3(target_f[1].physics.location)) - Vec3(target_f[1].physics.location)).rescale(134.85)
            else:
                bpos = Vec3(target_f[0].physics.location)
            mode_index = 3 * bool(aerial) + (1 + bool(double_jump)) * bool(not flick and not aerial)
            controls.throttle = 1 - 2 * bool(wait_for_fall[(1 + bool(double_jump)) * bool(not flick)] >= 0 and car_velocity.flat().length() * target_t[(1 + bool(double_jump)) * bool(not flick)] > car_location.flat().dist(bpos.flat()) and (car_velocity.length() == 0 or car_velocity.ang_to(front_direction) < math.pi / 2))
            controls.boost = my_car.has_wheel_contact == True and controls.throttle == 1 and car_velocity.length() < 2299
            controls.steer = steer_toward_target(my_car, bpos.flat())
            # In goal safety
            if bpos.y * sign(goal_location.y) <= -5030 and abs(bpos.x) >= 1000 and abs(car_location.x) < 900:
                rel_pos = Vec3(sign(bpos.x) * (450 + car_location.x * sign(bpos.x) / 2), sign(-goal_location.y) * 5070, 0)
                if (rel_pos - car_location).flat().rescale((bpos - car_location).flat().length()).y * sign(goal_location.y) > bpos.y * sign(goal_location.y):
                    controls.steer = steer_toward_target(my_car, rel_pos)
            # Jumping
            if aerial == True and my_car.boost / 100 * 3 >= target_t[3] + 0.1 * bool(my_car.has_wheel_contact) and wait_for_fall[(1 + bool(double_jump and False)) * bool(not flick)] >= 0:
                offset = bpos - (car_location + car_velocity * target_t[3] + Vec3(0, 0, -325) * target_t[3]**2) + up_direction * 292 * bool(not my_car.double_jumped)
                if my_car.has_wheel_contact == False:
                    if my_car.boost / 100 * 3 >= target_t[3]:
                        point_toward(offset)
                        controls.boost = front_direction.ang_to(offset) < math.pi / 4
                        controls.throttle = 1
                        controls.jump = my_car.double_jumped == False and (abs(packet.game_info.frame_num - self.jump_tick) < 24 or self.prev_jump == False)
                        if controls.jump == True and self.prev_jump == False:
                            controls.pitch, controls.yaw, controls.roll = 0, 0, 0
                    else:
                        recover(bpos)
                else:
                    if steer_toward_target(my_car, bpos) <= 0.2:
                        controls.jump = True
                    point_toward(offset)
            elif flick == True:
                recover(bpos)
                jt, ja = new_jump_time(max(bpos.z - 130, 0), False)
                if (round((target_t[0] - jt) * 120) <= 0 and my_car.has_wheel_contact == True) or (my_car.has_wheel_contact == False and self.prev_jump == True):
                    controls.jump = True
                if my_car.has_wheel_contact == False:
                    if (ball_location.z - car_location.z - 130) <= (car_velocity.z - ball_velocity.z) / (30 * (1 + bool(self.prev_jump == False))) and car_location.flat().dist(ball_location.flat()) <= 92.75:
                        controls.jump = not self.prev_jump
                        if controls.jump == True:
                            controls.yaw = 1
            elif double_jump == True:
                recover(bpos)
                jt, ja = new_jump_time(max(bpos.z, 0), True)
                if my_car.has_wheel_contact == True:
                    controls.jump = round((target_t[2] - jt) * 120) <= 0
                else:
                    if abs(packet.game_info.frame_num - self.jump_tick) < 24:
                        controls.jump = True
                    else:
                        controls.jump = not self.prev_jump
                        if controls.jump == True and self.prev_jump == False and my_car.double_jumped == False:
                            controls.pitch, controls.yaw, controls.roll = 0, 0, 0
                if my_car.double_jumped == True and car_velocity.z > 0:
                    if self.prev_wait == True:
                        point_toward(Vec3(0, 0, 1))
            else:
                recover(bpos)
                jt, ja = new_jump_time(max(bpos.z, 0), False)
                if (round((target_t[1] - jt) * 120) <= 0 and my_car.has_wheel_contact == True) or (my_car.has_wheel_contact == False and self.prev_jump == True) or ((car_location + car_velocity / 20 + Vec3(0, 0, -325) / 400).dist(Vec3(ball_states[3].physics.location)) <= 150 and my_car.has_wheel_contact == True):
                    controls.jump = True
                if my_car.has_wheel_contact == False:
                    if (car_location + car_velocity / 60 + Vec3(0, 0, -325) / 3600).dist(Vec3(ball_states[1].physics.location)) <= 150:
                        controls.jump = not self.prev_jump
                        if controls.jump == True:
                            controls.pitch = -math.floor(math.cos(front_direction.flat().ang_to(Vec3(ball_states[1].physics.location).flat() - (car_location + car_velocity / 60).flat())) + 0.5)
                            controls.yaw = math.floor(math.cos(right_direction.flat().ang_to(Vec3(ball_states[1].physics.location).flat() - (car_location + car_velocity / 60).flat())) + 0.5)
                    elif (car_location + car_velocity / 30 + Vec3(0, 0, -325) / 900).dist(Vec3(ball_states[2].physics.location)) <= 150:
                        controls.jump = False
            
            if my_car.has_wheel_contact == True:
                self.prev_wait = wait_for_fall[mode_index] >= 0
            self.renderer.draw_line_3d(bpos, car_location, self.renderer.green())

        def defense(goalie = False):
            # Get potential boost pads
            best_pad = None
            if my_car.boost < 100:
                best_score = math.inf
                for i in range(len(self.get_field_info().boost_pads)):
                    pad = self.get_field_info().boost_pads[i]
                    best_score = math.inf
                    if (abs(pad.location.x) > 3200 or abs(pad.location.y) > 4200) and Vec3(pad.location).dist(-goal_location) < car_location.dist(-goal_location) and sign(pad.location.x) == sign(car_location.x):
                        if packet.game_boosts[i].is_active == True or packet.game_boosts[i].timer <= (Vec3(pad.location) - car_location).length() / 2300:
                            score = Vec3(pad.location).dist(car_location) + Vec3(pad.location).dist(-goal_location)
                            if score < best_score:
                                best_pad = pad
                                best_score = score
            if best_pad != None:
                tl = Vec3(best_pad.location)
            else:
                if goalie == True:
                    tl = Vec3(0, -goal_location.y - sign(goal_location.y) * 150, 0)
                else:
                    tl = Vec3(sign(car_location.x) * 900, -goal_location.rescale(5050).y, 0)
            if car_location.dist(-goal_location) <= 1500:
                if car_velocity.length() <= 100 and car_location.y * sign(goal_location.y) <= -5120 + 100 * bool(goalie == False) and get_angle(front_direction, ball_location - car_location) >= 0.2:
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
            else:
                controls.throttle = 1
                controls.boost = best_pad != None and best_pad.is_full_boost == True
                controls.handbrake = get_angle(car_velocity, front_direction) > math.pi / 4 and get_angle(front_direction, tl - car_location) > math.pi / 4 and Vec3(my_car.physics.angular_velocity).length() >= min(car_velocity.length() / 500, 2)
                controls.steer = steer_toward_target(my_car, tl)
                if abs(controls.steer) <= 0.01 and car_velocity.flat().length() >= 1000 and car_location.flat().dist(tl.flat()) >= car_velocity.flat().length() * 1.4 + 500 * 1.5 + car_velocity.flat().length()**2 / 7000:
                    override = self.begin_front_flip(packet)
            recover(tl)
            self.renderer.draw_line_3d(tl, car_location, self.renderer.red())
        
        def positioning(pos, vel):
            default_d = pos.flat().dist(car_location.flat())
            next_d = (pos + vel).flat().dist(car_location.flat()) - car_velocity.length()
            tl = pos.flat() + vel.flat() * -default_d / (default_d - next_d)
        
        def recover(tl):
            nb = next_bounce(car_location, car_velocity, 17, 650)
            npos = car_location + car_velocity * nb + Vec3(0, 0, -325) * nb**2
            if car_velocity.flat().length() > 0 and car_velocity.flat().ang_to((tl - npos).flat()) > math.pi / 2:
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
            air_nb = air_pos(ball_location, ball_velocity, nb)
            air_nb2 = air_pos(ball_location, -ball_velocity, nb2)
            # The strategy
            closest_to_ball = [None, math.inf]
            furthest_back = [None, math.inf]
            if (abs(ball_location.y + goal_location.y) <= 1000 and abs(ball_location.x) >= 900): # Side wall clears
                for i in other_cars[0]:
                    cpos = Vec3(packet.game_cars[i].physics.location)
                    if min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y) < furthest_back[1]:
                        furthest_back = [i, min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)]
                    if cpos.dist(ball_location) <= closest_to_ball[1] and ball_location.x * sign(ball_location.x) >= cpos.x * sign(ball_location.x):
                        closest_to_ball = [i, cpos.dist(ball_location)]
            elif (abs(air_nb.y + goal_location.y) <= 100 and air_nb.z > 0) or (abs(air_nb2.y + goal_location.y) <= 100 and air_nb2.z > 0): # Backwall bounces
                if abs(air_nb.y - goal_location.y) < abs(air_nb2.y - goal_location.y):
                    bpos = air_nb
                else:
                    bpos = air_nb2
                for i in other_cars[0]:
                    cpos = Vec3(packet.game_cars[i].physics.location)
                    if min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y) < furthest_back[1]:
                        furthest_back = [i, min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)]
                    if cpos.dist(ball_location) <= closest_to_ball[1] and abs(cpos.y - goal_location.y) + abs(cpos.x - bpos.x) / 5 > abs(bpos.y - goal_location.y):
                        closest_to_ball = [i, cpos.dist(ball_location)]
            else:
                for i in other_cars[0]:
                    cpos = Vec3(packet.game_cars[i].physics.location)
                    if min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y) < furthest_back[1]:
                        furthest_back = [i, min(cpos.dist(-goal_location), 900) + abs(cpos.y + goal_location.y)]
                    if cpos.dist(ball_location) + 5000 * bool(math.sin(packet.game_cars[i].physics.rotation.yaw) * goal_location.y < 0 or cpos.flat().dist(Vec3(sign(cpos.x, 1) * 900, -goal_location.y, 0)) <= 100) <= closest_to_ball[1] and abs(cpos.y - goal_location.y) + abs(cpos.x - ball_location.x) / 5 > abs(ball_location.y - goal_location.y):
                        closest_to_ball = [i, cpos.dist(ball_location) + 5000 * bool(math.sin(packet.game_cars[i].physics.rotation.yaw) * goal_location.y < 0 or cpos.flat().dist(Vec3(sign(cpos.x, 1) * 900, -goal_location.y, 0)) <= 100)]
            if closest_to_ball[0] == self.index:
                li = shot_variables(target_func)
                shoot_ball(target_func, li, double_jump = li[0][2] < li[0][1], aerial = True) # target_t, target_f, wait_for_fall
                self.renderer.draw_string_3d(car_location, 1, 1, "Shoot", self.renderer.green())
            elif furthest_back[0] == self.index:
                defense(True)
                self.renderer.draw_string_3d(car_location, 1, 1, "Side", self.renderer.yellow())
            else:
                defense(False)
                self.renderer.draw_string_3d(car_location, 1, 1, "Goalie", self.renderer.red())

        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        car_rotation = my_car.physics.rotation
        rot_vel = [(car_rotation.pitch - self.prev_rot[0]) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1), yaw_conversion(self.prev_rot[1], car_rotation.yaw) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1) * math.cos(car_rotation.pitch), roll_conversion(self.prev_rot[2], car_rotation.roll) * 120 / max(abs(packet.game_info.frame_num - self.prev_frame_nr), 1)]
        front_direction = car_dir(car_rotation.pitch, car_rotation.yaw)
        right_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll + math.pi / 2)
        up_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll)
        max_jump_height = [new_max_jump_height(False), new_max_jump_height(True)]
        travel_d, travel_v = get_acceleration(car_velocity.length())
        goal_location = Vec3(0, 5120 * (1 - 2 * bool(self.team == 1)), 0)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        ball_prediction = self.get_ball_prediction_struct()
        ball_states = get_preds()
        save_deadline = goal_time()
        override = None

        # ball_study = pred_analysis()
        controls = SimpleControllerState()
        # shoot_ball(goal_location, False, aerial = True)
        if packet.game_info.is_round_active == True:
            general_strategy()

        if controls.jump == True and self.prev_jump == False and my_car.has_wheel_contact == True:
            self.jump_tick = packet.game_info.frame_num

        self.prev_jump = controls.jump
        self.prev_frame_nr = packet.game_info.frame_num
        self.prev_rot = [car_rotation.pitch, car_rotation.yaw, car_rotation.roll]

        if override:
            return override
        else:
            return controls

    def begin_front_flip(self, packet):
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        self.active_sequence = Sequence([
            ControlStep(duration=0.08, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.65, controls=SimpleControllerState(jump=True, pitch=-1)),
        ])

        return self.active_sequence.tick(packet)