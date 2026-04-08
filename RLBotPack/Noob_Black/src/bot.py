from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.orientation import Orientation, relative_location
from util.vec import Vec3
from util.moremath import *

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
        self.on_wall = False
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
        
        def point_toward(aerial_front):
            vd_pitch, vd_yaw = aerial_control(aerial_front, car_rotation, 1)
            c_pitch = vd_pitch - math.sqrt(abs(rot_vel[0]) / 6.23) * sign(rot_vel[0]) * math.cos(car_rotation.roll - rot_vel[2] / 120) - math.sqrt(abs(rot_vel[1]) / 6.23) * sign(rot_vel[1]) * math.sin(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch)
            c_yaw = vd_yaw - math.sqrt(abs(rot_vel[1]) / 4.555) * sign(rot_vel[1]) * math.cos(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch) - math.sqrt(abs(rot_vel[0]) / 4.555) * sign(rot_vel[0]) * -math.sin(car_rotation.roll - rot_vel[2] / 120)
            if abs(c_pitch) > abs(c_yaw):
                c_pitch, c_yaw = c_pitch / abs(c_pitch), c_yaw / abs(c_pitch)
            elif abs(c_yaw) > abs(c_pitch):
                c_pitch, c_yaw = c_pitch / abs(c_yaw), c_yaw / abs(c_yaw)
            controls.pitch, controls.yaw = c_pitch, c_yaw
        
        def new_jump_time(h, double):
            single_time = solve_quadratic(-325.0556640625, 564.9931640625, -11.6591796875, min(h, max_jump_height[0]), -1)
            if single_time >= 24 / 120:
                if single_time >= 25 / 120 and double:
                    return solve_quadratic(-325.0556640625, 856.9931640625, -11.6591796875 - 292 * 25 / 120, min(h, max_jump_height[1]), -1), 2
                else:
                    return single_time, 1
            else:
                return solve_quadratic(392.2802734375, 272.7626953125, 17.671875, h, 1), 1
        
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
        
        def shot_variables_wall(target):
            # Get the maximum time
            max_t = 5
            if save_deadline >= 0:
                max_t = save_deadline
            # Get the best prediction to shoot at
            target_t = [max_t, max_t, max_t, max_t]
            target_f = [ball_states[round(max_t * 60)], ball_states[round(max_t * 60)], ball_states[round(max_t * 60)], ball_states[round(max_t * 60)]]
            wait_for_fall = [-1, -1, -1, 0]
            air_t = 0
            jump_vec = (292 * bool(not my_car.double_jumped) + 146 * bool(not my_car.jumped) + 146 / 24 * max(24 - abs(packet.game_info.frame_num - self.jump_tick), 0))
            #
            def hit_d_check(bpos, t):
                np = bpos - offset_vec * 134.85
                jt, ja = new_jump_time_wall(get_dist_from_wall(np), 0)
                np = np + Vec3(0, 0, 325 * jt**2)
                dt = used_f(car_location, np).dist(used_f2(car_location))
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def hit_double_check(bpos, t):
                np = bpos - offset_vec * 92.75
                jt, ja = new_jump_time_wall(get_dist_from_wall(np), 1)
                np = np + Vec3(0, 0, 325 * jt**2)
                dt = used_f(car_location, np).dist(used_f2(car_location))
                ticks_charging = round(t * 120)
                ticks_driving = round(min(max(t - jt, 0), 5) * 120)
                return travel_d[ticks_driving] + travel_v[ticks_driving] * (ticks_charging - ticks_driving) / 120 >= dt
            def aerial_d_check(bpos, t):
                np = bpos - offset_vec * 92.75
                dt = np.dist(car_location + car_velocity * t + Vec3(0, 0, -325) * air_t + up_direction * jump_vec)
                return dt <= 2975 / 6 * air_t
            # 
            if car_location.z <= 50:
                used_f = ball_from_ground
                used_f2 = car_flat
            elif 4096 - abs(car_location.x) < 5120 - abs(car_location.y):
                used_f = ball_x_to_y
                used_f2 = car_xwall
            else:
                used_f = ball_y_to_x
                used_f2 = car_ywall
            # Get the best prediction to shoot at
            for i in range(round(max_t * 60) + 1):
                t = i / 60
                bp = ball_states[i]
                bpos = Vec3(bp.physics.location)
                target_p = target(bpos)
                offset_vec = (target_p - bpos).normalized()
                if target_t[0] == max_t and hit_d_check(bpos, t):
                    if new_jump_time_wall(get_dist_from_wall(bpos - offset_vec * 134.85), 0)[0] > 1.45:
                        if wait_for_fall[0] == -1:
                            wait_for_fall[0] = t
                    else:
                        target_t[0] = t
                        target_f[0] = bp
                if target_t[1] == max_t and hit_double_check(bpos, t):
                    if new_jump_time_wall(get_dist_from_wall(bpos - offset_vec * 92.75), 1)[0] > 1.45:
                        if wait_for_fall[1] == -1:
                            wait_for_fall[1] = t
                    else:
                        target_t[1] = t
                        target_f[1] = bp
                if target_t[3] == max_t: # Aerials
                    if aerial_d_check(bpos, t):
                        target_t[3] = t
                        target_f[3] = bp
                    else:
                        air_t += (2 * i + 1) / 3600
            return [target_t, target_f, wait_for_fall]

        def shoot_ball(target, li, other_cars, flick = False, double_jump = False, aerial = False, delay = False):
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
            # Delays
            if delay == True: # Wait for the ball to align better with the goal before shooting
                if abs(og_bpos.x) < 3000 and abs(og_bpos.x) - 890 + 92.75 * math.sqrt(2) > abs(og_bpos.y - goal_location.y) and bvel.x * sign(og_bpos.x) < 0:
                    for i in range(round(target_t[grounded_mode_index] * 60), 301):
                        new_bpos = Vec3(ball_states[i].physics.location)
                        if abs(new_bpos.x) - 890 + 92.75 * math.sqrt(2) <= abs(new_bpos.y - goal_location.y):
                            og_bpos = new_bpos
                            bvel = Vec3(ball_states[i].physics.velocity)
                            if flick == True:
                                bpos = og_bpos
                            elif double_jump == True:
                                bpos = og_bpos - (target(og_bpos) - og_bpos).rescale(92.75)
                            else:
                                bpos = og_bpos - (target(og_bpos) - og_bpos).rescale(134.85)
                            target_t[grounded_mode_index] = i / 60
                            target_f[grounded_mode_index] = ball_states[i]
                            jt, ja = new_jump_time(max(bpos.z, 0), flick == False and double_jump == True)
                            jt = round(jt * 120)
                            if travel_d[i * 2 - jt - 1] + travel_v[i * 2 - jt - 1] * jt / 120 >= car_location.flat().dist(bpos.flat()):
                                wait_for_fall[grounded_mode_index] = (i - 1) / 60
                            break
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
                if (round((target_t[0] - jt) * 120) <= 0 and my_car.has_wheel_contact == True) or (my_car.has_wheel_contact == False and self.prev_jump == True):
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
                if (og_bpos.z <= 110 and bvel.z <= 100 and packet.game_info.is_kickoff_pause == False and abs(og_bpos.y - goal_location.y) - 92.75 >= (abs(car_velocity.y)**2 - 1000**2) / 1500):
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
                if (og_bpos.z <= 110 and bvel.z <= 100 and packet.game_info.is_kickoff_pause == False and abs(og_bpos.y - goal_location.y) - 92.75 >= (abs(car_velocity.y)**2 - 1000**2) / 1500):
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
        
        def wall_shot(target, li, double_jump, aerial):
            target_t, target_f, wait_for_fall = li[0], li[1], li[2]
            used_index = double_jump
            will_aerial = aerial == True and my_car.boost / 100 * 3 >= target_t[3] + 0.1 * bool(my_car.has_wheel_contact) and wait_for_fall[used_index] >= 0
            if car_location.z <= 50:
                used_f = ball_from_ground
                used_f2 = car_flat
            elif 4096 - abs(car_location.x) < 5120 - abs(car_location.y):
                used_f = ball_x_to_y
                used_f2 = car_xwall
            else:
                used_f = ball_y_to_x
                used_f2 = car_ywall
            # 
            target_bpos = Vec3(target_f[used_index].physics.location)
            target_og_pos = target_bpos - (target(target_bpos) - target_bpos).rescale(134.85 * bool(used_index == 0))
            jt, ja = new_jump_time_wall(get_dist_from_wall(target_og_pos), used_index)
            target_og_pos += Vec3(0, 0, 325 * jt**2)
            target_pos = used_f(car_location, target_og_pos)
            d_travelled = target_pos.dist(used_f2(car_location))
            controls.throttle = 1 - 2 * bool(wait_for_fall[used_index] >= 0 and car_velocity.flat().length() * target_t[used_index] > used_f2(car_location).dist(target_pos) and (car_velocity.length() == 0 or car_velocity.ang_to(front_direction) < math.pi / 2))
            controls.boost = my_car.has_wheel_contact == True and controls.throttle == 1 and car_velocity.length() < 2299 and wait_for_fall[used_index] < 0
            controls.steer = steer_toward_target(my_car, target_pos)
            # Controls
            if will_aerial == True:
                offset = target_bpos - (car_location + car_velocity * target_t[3] + Vec3(0, 0, -325) * target_t[3]**2) + up_direction * 292 * bool(not my_car.double_jumped)
                if my_car.has_wheel_contact == False:
                    if my_car.boost / 100 * 3 >= target_t[3]:
                        point_toward(offset)
                        controls.boost = front_direction.ang_to(offset) < math.pi / 4
                        controls.throttle = 1
                        controls.jump = my_car.double_jumped == False and (abs(packet.game_info.frame_num - self.jump_tick) < 24 or self.prev_jump == False)
                        target_roof_dir = (target_bpos - car_location)
                        controls.roll = sign(math.pi / 2 - get_angle(target_roof_dir, right_direction))
                        if my_car.jumped == True and controls.jump == True and self.prev_jump == False:
                            controls.pitch, controls.yaw, controls.roll = 0, 0, 0
                    else:
                        recover(target_bpos)
                else:
                    if steer_toward_target(my_car, target_bpos) <= 0.2:
                        controls.jump = True
                    point_toward(offset)
            else:
                if used_index == 0:
                    if ((round((target_t[0] - jt) * 120) <= 0 and my_car.has_wheel_contact == True and get_angle(front_direction, target_og_pos - car_location) <= math.pi / 2) or (my_car.has_wheel_contact == False and self.prev_jump == True) or ((car_location + car_velocity / 20 + Vec3(0, 0, -325) / 400).dist(Vec3(ball_states[3].physics.location)) <= 150 and my_car.has_wheel_contact == True)):
                        controls.jump = True
                    if my_car.has_wheel_contact == True:
                        if wait_for_fall[used_index] == -1:
                            controls.throttle = 1
                            controls.boost = True
                        else:
                            controls.throttle = sign(d_travelled * safe_div(target_t[0]) - car_velocity.length())
                            controls.boost = controls.throttle == 1
                    else:
                        if abs(packet.game_info.frame_num - self.jump_tick) >= 24:
                            point_toward((ball_location - car_location).flat())
                        if (car_location + car_velocity / 60 + Vec3(0, 0, -325) / 3600).dist(Vec3(ball_states[1].physics.location)) <= 150 or packet.game_ball.latest_touch.player_index == self.index != self.prev_touch[0]:
                            controls.jump = not self.prev_jump
                            if controls.jump == True:
                                controls.pitch = -math.floor(math.cos(front_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
                                controls.yaw = math.floor(math.cos(right_direction.flat().ang_to(Vec3(ball_states[0].physics.location).flat() - car_location.flat())) + 0.5)
                        elif (car_location + car_velocity / 30 + Vec3(0, 0, -325) / 900).dist(Vec3(ball_states[2].physics.location)) <= 150:
                            controls.jump = False
            self.renderer.draw_line_3d(target_pos, car_location, self.renderer.green())
            self.renderer.draw_rect_3d(target_og_pos, 8, 8, True, self.renderer.green(), centered=True)
            self.renderer.draw_rect_3d(target_pos, 8, 8, True, self.renderer.cyan(), centered=True)
            controls.use_item = True
        
        def generic_demo(target):
            target_car = packet.game_cars[target]
            target_pos = Vec3(target_car.physics.location)
            target_vel = Vec3(target_car.physics.velocity)
            relative_position = target_pos - car_location
            t = solve_quadratic(target_vel.x**2 + target_vel.y**2 + target_vel.z**2 - car_velocity.length()**2, 2 * (relative_position.x * target_vel.x + relative_position.y * target_vel.y + relative_position.z * target_vel.z), relative_position.x**2 + relative_position.y**2 + relative_position.z**2, 0, 1)
            if t == None:
                t = 0
            controls.steer = steer_toward_target(my_car, target_pos + target_vel * t)
            controls.throttle = 1
            controls.boost = True

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
        # The general purpose strategy, weak in 1s, good in 2s but best in 3s
        def general_strategy():
            # Team positioning
            # Strategy variables
            nb = next_bounce(ball_location, ball_velocity, 92.75, 650)
            nb2 = next_bounce(ball_location, -ball_velocity, 92.75, 650)
            nb3 = next_bounce(ball_location, ball_velocity, max_jump_height[1], 650)
            nb31 = next_bounce(ball_location, Vec3(0, 0, ball_velocity.z), max_jump_height[1], 650)
            nbw = next_bounce_horizontal(ball_location, ball_velocity, 92.75)
            air_nb = air_pos(ball_location, ball_velocity, nb)
            air_nb2 = air_pos(ball_location, -ball_velocity, nb2)
            air_nb3 = air_pos(ball_location, ball_velocity, nb3)
            air_nbw = (ball_location + ball_velocity * nbw).flat()
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
                        # biggest_dependency = abs(cpos.y - goal_location.y) + abs(cpos.x - ball_location.x) / 5 * bool(save_deadline >= 0) > ball_dependency
                        biggest_dependency = abs(cpos.y - goal_location.y) + abs(cpos.x - ball_location.x) / 5 * bool(save_deadline >= 0) > ball_dependency and (abs(math.sin(get_angle(cpos.flat() - ball_location.flat(), ball_velocity.flat()))) * (cpos.flat() - ball_location.flat()).length() * ball_velocity.flat().length() / 2300 - 134.85 < abs(math.cos(get_angle(cpos.flat() - ball_location.flat(), ball_velocity.flat()))) * (cpos.flat() - ball_location.flat()).length() or save_deadline < 0)
                        if furthest_score < furthest_back[1]:
                            furthest_back = [i, furthest_score]
                        if (closest_score <= closest_to_ball[1] and bool(biggest_dependency) >= closest_to_ball[2]) or bool(biggest_dependency) > closest_to_ball[2]:
                            closest_to_ball = [i, closest_score, bool(biggest_dependency)]
            if closest_to_ball[0] == self.index:
                x_wall_to_use = 4096 - abs(ball_location.x) < 5120 - abs(ball_location.y)
                y_wall_to_use = not x_wall_to_use
                roll_up_wall_condition = ball_location.z + ball_velocity.z**2 / 1300 <= 92.75 + 36.25 - 18.125 * bool(abs(air_nbw.y) >= 5120) and str(nbw) != "nan" and car_location.flat().dist(air_nbw) > travel_d[min(round(nbw) * 120, 599)] and ((x_wall_to_use and abs(ball_velocity.x)**2 / 1300 >= 400) or (y_wall_to_use and abs(ball_velocity.y)**2 / 1300 >= 400 and abs(car_rotation.roll) > math.pi / 4 and ball_location.y * goal_location.y < 0))
                stable_up_wall_condition = new_jump_time_wall(min(4096 - abs(ball_location.x), 5120 - abs(ball_location.y)), 0)[0] <= 1.45 and ((x_wall_to_use and abs(ball_velocity.x) < 150) or (y_wall_to_use and abs(ball_velocity.y) < 150 and abs(car_rotation.roll) > math.pi / 4 and ball_location.y * goal_location.y < 0)) and ball_location.z + ball_velocity.z**2 / 1300 <= 1900 and (ball_velocity.z > 0 and ball_location.z + ball_velocity.z**2 / 1300 >= 400 or ball_location.z >= 400)
                go_up_wall = (roll_up_wall_condition or stable_up_wall_condition) and abs(air_nbw.y - goal_location.y) > 50
                if my_car.has_wheel_contact == False:
                    go_up_wall = self.on_wall
                if go_up_wall == True:
                    li = shot_variables_wall(target_func)
                    wall_shot(target_func, li, 0, True)
                    txt = "Shoot (Wall)"
                    if x_wall_to_use:
                        txt += ", X"
                    if y_wall_to_use:
                        txt += ", Y"
                    self.renderer.draw_string_3d(car_location, 1, 1, txt, self.renderer.green())
                else:
                    if packet.game_info.is_kickoff_pause == True:
                        tf = target_func_flat
                    else:
                        tf = target_func
                    li = shot_variables_2(tf)
                    to_double_jump = li[0][2] < li[0][1] and packet.game_info.is_kickoff_pause == False
                    shoot_ball(tf, li, other_cars, double_jump = to_double_jump, aerial = True, delay = True) # target_t, target_f, wait_for_fall
                    txt = "Shoot"
                    if to_double_jump:
                        txt += ", Double"
                    self.renderer.draw_string_3d(car_location, 1, 1, txt, self.renderer.green())
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
        # Get list of cars
        team_sizes = [0, 0]
        other_cars = [[self.index], []]
        for i in range(len(packet.game_cars)):
            if packet.game_cars[i].name != "":
                other_cars[bool(packet.game_cars[i].team != self.team)].append(i)
                team_sizes[bool(packet.game_cars[i].team != self.team)] += 1
                
        controls = SimpleControllerState()
        if packet.game_info.is_round_active == True:
            general_strategy()

        if controls.jump == True and self.prev_jump == False and my_car.has_wheel_contact == True:
            self.jump_tick = packet.game_info.frame_num
            self.just_flipped = -10000
            self.prev_touch = [packet.game_ball.latest_touch.player_index, packet.game_ball.latest_touch.time_seconds]
        if my_car.double_jumped == False and my_car.jumped == True and controls.jump == True and self.prev_jump == False and not (controls.yaw == controls.pitch == controls.roll == 0):
            self.just_flipped = packet.game_info.frame_num

        self.prev_jump = controls.jump
        self.prev_frame_nr = packet.game_info.frame_num
        self.prev_rot = [car_rotation.pitch, car_rotation.yaw, car_rotation.roll]
        if my_car.has_wheel_contact == True:
            self.on_wall = car_location.z > 50

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