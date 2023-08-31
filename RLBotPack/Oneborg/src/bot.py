from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import *
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
from util.scummy_util import *
import math, random
from queue import Empty

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.jumping = 0
        self.jump_flip = False
        self.last_surface = Vec3(0, 0, 0)

    def initialize_agent(self):
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        match_settings = self.get_match_settings()
        mutators = match_settings.MutatorSettings()
        self.gamemode = match_settings.GameMode()
        # Ball size
        self.ball_size_setting = mutators.BallSizeOption()
        if self.ball_size_setting == 0:
            self.ball_size_setting = 92.75
        elif self.ball_size_setting == 1:
            self.ball_size_setting = 67.05
        elif self.ball_size_setting == 2:
            self.ball_size_setting = 144.2
        elif self.ball_size_setting == 3:
            self.ball_size_setting = 221.54
        # Boost strength
        self.boost_strength_setting = mutators.BoostStrengthOption()
        if self.boost_strength_setting == 0:
            self.boost_strength_setting = 5950 / 6
        elif self.boost_strength_setting == 1:
            self.boost_strength_setting = 5950 / 4
        elif self.boost_strength_setting == 2:
            self.boost_strength_setting = 5950 / 3
        elif self.boost_strength_setting == 3:
            self.boost_strength_setting = 59500 / 6
        print(self.boost_strength_setting)
        self.dropshot = self.gamemode == 2
        self.aerial_situation = "Free"
        self.dropshot_goals = []
        if self.dropshot == True:
            for i in range(140):
                self.dropshot_goals.append(0)
        self.kickoff = 0
        self.no_hold_off_time = 0
        # Aerial Information
        self.prev_rot = None

    def recieve_comm(self):
        try:
            msg = self.matchcomms.incoming_broadcast.get_nowait()
            if "tmcp_version" in msg and msg["team"] == self.team:
                if msg["aerial"] == False:
                    self.aerial_situation = "Free"
                elif msg["index"] == self.index:
                    self.aerial_situation = "Committing"
                else:
                    self.aerial_situation = "Stay"
        except:
            pass

    def send_comm(self, aerial, i):
        sending = {
            "tmcp_version": [1, 0],
            "team": self.team,
            "index": i,
            "aerial": aerial,
        }
        self.matchcomms.outgoing_broadcast.put_nowait(sending)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.boost_pad_tracker.update_boost_status(packet)
        
        self.recieve_comm()

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        # Get send location
        def get_send():
            if self.dropshot == True:
                return Vec3(0, 2560 * sign(0.5 - self.team), -2560 * sign(ball_location.y) * sign(0.5 - self.team)), Vec3(0, 2560 * sign(0.5 - self.team), -2560 * sign(ball_location.y) * sign(0.5 - self.team))
            else:
                return Vec3(clamp(car_location.x, -800, 800), 5120 * sign(0.5 - self.team), 0), Vec3(0, 5120 * sign(0.5 - self.team), 0)
        # Update the location based on others
        def update_send(pos):
            updated = pos
            if get_angle(pos - car_location, Vec3(nearest_enemy.physics.location) - car_location) <= math.atan(nearest_ft * safe_div(nearest_et)) and nearest_et >= nearest_ft:
                triangle_angle = get_angle(ball_location - Vec3(nearest_enemy.physics.location), Vec3(nearest_enemy.physics.velocity))
                corner = Vec3(nearest_enemy.physics.location) + Vec3(nearest_enemy.physics.velocity) * (ball_location - Vec3(nearest_enemy.physics.location)).length() * safe_div(Vec3(nearest_enemy.physics.velocity).length() * math.tan(triangle_angle))
                updated = ball_location + (ball_location - corner)
            return updated
        # Get the number of players
        def player_count():
            friendly = 0
            enemy = 0
            for other_p in packet.game_cars:
                if other_p.physics.location.z != 0:
                    if other_p.team == self.team:
                        friendly += 1
                    else:
                        enemy += 1
            return friendly, enemy
        # Distance order
        def distance_order():
            def get_score(car):
                return (Vec3(car.physics.location) - ball_location).length() + get_angle(Vec3(math.cos(car.physics.rotation.yaw) * math.cos(car.physics.rotation.pitch), math.sin(car.physics.rotation.yaw) * math.cos(car.physics.rotation.pitch), math.sin(car.physics.rotation.pitch)), ball_location)
            def valid_attacker(car):
                return get_angle(ball_location - Vec3(car.physics.location), ball_location - send_location) > math.pi / 2 or get_angle(ball_location - Vec3(car.physics.location), ball_location + send_location) <= math.pi / 2
            i = 1
            ref = get_score(my_car)
            if my_car.has_wheel_contact == True:
                if valid_attacker(my_car):
                    for other_p in packet.game_cars:
                        if other_p.team == self.team and other_p.physics.location.z > 10 and (valid_attacker(other_p) or self.dropshot == True):
                            if get_score(other_p) < ref:
                                i += 1
                else:
                    i = 0
            return i
        # Read other players
        def read_players(offset, team_type):
            nearest_p = None
            nearest_t = math.inf
            nearest_k = 1
            for other_p in packet.game_cars:
                if other_p.name != "" and bool(other_p.team == self.team) == bool(team_type):
                    t = predict_surface_bounce(Vec3(other_p.physics.location), Vec3(other_p.physics.velocity), 20, -packet.game_info.world_gravity_z) * bool(not other_p.has_wheel_contact)
                    if other_p.has_wheel_contact == False and (ball_location - Vec3(other_p.physics.location)).length() * safe_div((ball_velocity - Vec3(other_p.physics.velocity)).length()) < t and will_intersect(ball_location - Vec3(other_p.physics.location), ball_velocity - Vec3(other_p.physics.velocity), self.ball_size_setting + 65.755):
                        offset_pos = ball_location - Vec3(other_p.physics.location)
                        offset_vel = ball_velocity - Vec3(other_p.physics.velocity)
                        val = (ball_location - Vec3(other_p.physics.location)).length() * safe_div((ball_velocity - Vec3(other_p.physics.velocity)).length())
                        if val < nearest_t:
                            nearest_t = val
                            nearest_p = other_p
                            nearest_k = 1
                    else:
                        o_pos = freefall(Vec3(other_p.physics.location), Vec3(other_p.physics.velocity), -packet.game_info.world_gravity_z, t)
                        o_vel = Vec3(other_p.physics.velocity) + Vec3(0, 0, packet.game_info.world_gravity_z) * t
                        o_vel = o_vel * clamp(o_vel.length(), 0, 2300) * safe_div(o_vel.length())
                        if abs(surface_pos(o_pos, self.dropshot).x) == 4096:
                            o_vel = Vec3(0, o_vel.y, o_vel.z)
                        elif abs(surface_pos(o_pos, self.dropshot).y) == 5120:
                            o_vel = Vec3(o_vel.x, 0, o_vel.z)
                        elif surface_pos(o_pos, self.dropshot).z == 0:
                            o_vel = Vec3(o_vel.x, o_vel.y, 0)
                        offset_pos = ball_location - o_pos
                        offset_vel = ball_velocity - o_vel
                        val = (offset_pos.length() - self.ball_size_setting) * safe_div(offset_vel.length() + offset) + t + get_angle(offset_vel, -offset_pos)
                        if val < nearest_t:
                            nearest_t = val
                            nearest_p = other_p
                            nearest_k = (offset_vel.length() + offset) * safe_div(offset_vel.length())
            return nearest_p, nearest_t * nearest_k**0
        # Predict where the ball will be
        def predict_ball(t):
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + clamp(t, 0, 5))
            if ball_in_future is not None:
                return ball_in_future
            else:
                return packet.game_ball
        # Is it fitting to attack
        def fit_to_attack(pos):
            if (pos + send_location).length() > (ball_location + send_location).length():
                if (pos - send_location).length() > (ball_location - send_location).length():
                    return True
            else:
                if get_angle(-send_location - ball_location, car_location - ball_location) <= math.pi / 2:
                    return True
            return False
        # Curve for correction when hitting the ball
        def setup_curve(cl, tp, hp):
            return surface_pos(tp - (hp - tp) * safe_div((hp - tp).length()) * clamp((tp - cl).length() / 2, 0, (car_velocity - ball_velocity).length()), self.dropshot)
        # Jump over cars to prevent collision
        def avoid_bump():
            for i in range(len(packet.game_cars)):
                if i != self.index and packet.game_cars[i].physics.location.z > 0 and packet.game_cars[i].has_wheel_contact == True:
                    vel = car_velocity
                    vel2 = Vec3(packet.game_cars[i].physics.velocity)
                    bl = not bool(clamp((vel + vel2).length(), 0, 2300) * math.cos(get_angle((vel + vel2) * safe_div((vel + vel2).length()) * clamp((vel + vel2).length(), 0, 2300), target_location - car_location)) <= vel.length() * math.cos(get_angle(car_velocity, target_location)) and vel2.length() < 2200)
                    pos = car_location + vel * 0.2 * bl
                    pos2 = Vec3(packet.game_cars[i].physics.location) + vel2 * 0.2 * bl
                    dist = (pos - pos2).length()
                    on_course = False
                    if dist > 254.04:
                        if get_angle(pos2 - pos, vel2 - vel) <= math.tan(math.sqrt(254.04**2 / (dist**2 - 254.04**2))):
                            on_course = True
                    else:
                        on_course = True
                    if on_course == True and dist <= 254.04 + (vel - vel2).length() / 2 and (vel.length() <= vel2.length() or packet.game_cars[i].team != self.team) and ((pos2 - pos) * safe_div((pos2 - pos).length()) * (ball_location - pos).length() - (ball_location - pos)).length() > self.ball_size_setting:
                        if my_car.has_wheel_contact == True and get_angle(vel - vel2, pos - pos2) > math.pi / 2:
                            self.jumping = 2 / 60
                        elif get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) < math.pi / 2 and (vel2 - vel).length() <= 300 and my_car.has_wheel_contact == False:
                            self.jumping = -1 / 60
                            override = self.generic_flip(packet, -flip_value(math.cos(get_angle(dir_convert(Vec3(side_direction.x, side_direction.y, 0)), dir_convert(Vec3(packet.game_cars[i].physics.location.x - car_location.x, packet.game_cars[i].physics.location.y - car_location.y, 0))))) * sign(roof_direction.z), -flip_value(math.cos(get_angle(dir_convert(Vec3(car_direction.x, car_direction.y, 0)), dir_convert(Vec3(packet.game_cars[i].physics.location.x - car_location.x, packet.game_cars[i].physics.location.y - car_location.y, 0))))), 0, 0, 0.8)
        # Find the boost pad
        def find_boost_pad(tl):
            best_pad = None
            best_score = math.inf
            for i in range(len(self.get_field_info().boost_pads)):
                pad = self.get_field_info().boost_pads[i]
                if (Vec3(pad.location) - Vec3(0, 0, 0)).length() >= 100 and (packet.game_boosts[i].is_active == True or packet.game_boosts[i].timer <= (Vec3(pad.location) - car_location).length() * safe_div(clamp(car_velocity.length(), 1410, 2300))) and get_angle(Vec3(predict_ball(intersection).physics.location) - Vec3(pad.location), send_location - Vec3(pad.location)) <= math.pi / 2:
                    full = pad.is_full_boost
                    if full:
                        benefit = clamp(100 - my_car.boost, 0, 100)
                    else:
                        benefit = clamp(100 - my_car.boost, 0, 12)
                    score = ((car_location - Vec3(pad.location)).length() + (tl - Vec3(pad.location)).length() - (car_location - tl).length()) * safe_div(benefit)
                    if score < best_score:
                        best_score = score
                        best_pad = pad
            if best_pad:
                tl = Vec3(best_pad.location)
            else:
                tl = tl
            return tl
        '''
        Actions
        '''
        # Try to land on a surface
        def recovery():
            # Prediction
            t = predict_surface_bounce(car_location, car_velocity, 20, -packet.game_info.world_gravity_z)
            ref_pos = car_location + car_velocity * t + Vec3(0, 0, packet.game_info.world_gravity_z / 2) * t**2
            # Surfaces
            su = ref_pos + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 0) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 0), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 0) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 0), math.cos(math.pi / 2 * 0) * math.cos(car_rotation.pitch))
            sl = ref_pos + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(-math.pi / 2 * 1) + math.sin(car_rotation.yaw) * math.sin(-math.pi / 2 * 1), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(-math.pi / 2 * 1) - math.cos(car_rotation.yaw) * math.sin(-math.pi / 2 * 1), math.cos(-math.pi / 2 * 1) * math.cos(car_rotation.pitch))
            sr = ref_pos + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 1) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 1), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 1) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 1), math.cos(math.pi / 2 * 1) * math.cos(car_rotation.pitch))
            sd = ref_pos + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 2) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 2), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 2) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 2), math.cos(math.pi / 2 * 2) * math.cos(car_rotation.pitch))
            spos = surface_pos(ref_pos, self.dropshot)
            best_s = get_smallest_i([(su - spos).length(), (sl - spos).length(), (sr - spos).length(), (sd - spos).length()])
            if best_s == 0:
                controls.roll = clamp(-car_rotation.roll, -1, 1)
            elif best_s == 1:
                controls.roll = clamp(-car_rotation.roll - math.pi / 2, -1, 1)
            elif best_s == 2:
                controls.roll = clamp(-car_rotation.roll + math.pi / 2, -1, 1)
            elif best_s == 3:
                controls.roll = clamp(-(math.pi - abs(car_rotation.roll)) * pref_sign(car_rotation.roll, random.choice([-1, 1])), -1, 1)
            tr = dir_convert(surface_pos(ref_pos + dir_convert(car_velocity + Vec3(0, 0, packet.game_info.world_gravity_z) * t), self.dropshot) - spos)
            if my_car.has_wheel_contact == False:
                if my_car.double_jumped == False and spos.z == 0:
                    ao = math.pi / 18
                    tr = dir_convert(tr * math.cos(ao) + Vec3(0, 0, math.sin(ao)))
                if t <= 1 / 60 and my_car.double_jumped == False and spos.z == 0:
                    self.jumping = 1 / 60
                    controls.pitch = -1
                    controls.yaw = random.randint(-1, 1)
                controls.pitch, controls.yaw = aerial_control(tr, car_rotation, 0.5, True)
        # Refueling
        def refuel():
            tl = find_boost_pad(target_location)
            controls.throttle = sign(math.pi / 2 - get_angle(car_velocity, car_direction))
            controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Goalie
        def goalie():
            return 1
        # Fly to get the ball
        def aerial():
            # Decide whether to double jump
            aerial_front_jump, aerial_intersection_jump = aerial_dir_x(car_location, car_velocity + roof_direction * 292, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, 1, 1, car_direction, packet)
            # Get the offset from the correct velocity
            vd_pitch, vd_yaw = aerial_control(aerial_front, car_rotation, 1, False)
            c_pitch = vd_pitch * 4.555 / 6.23 - math.sqrt(abs(pitch_velocity) / 6.23) * sign(pitch_velocity) * math.cos(car_rotation.roll) - math.sqrt(abs(yaw_velocity) / 6.23) * sign(yaw_velocity) * math.sin(car_rotation.roll) * math.cos(car_rotation.pitch)
            c_yaw = vd_yaw - math.sqrt(abs(yaw_velocity) / 4.555) * sign(yaw_velocity) * math.cos(car_rotation.roll) * math.cos(car_rotation.pitch) - math.sqrt(abs(pitch_velocity) / 4.555) * sign(pitch_velocity) * -math.sin(car_rotation.roll)
            if abs(c_pitch) > abs(c_yaw):
                c_pitch, c_yaw = c_pitch / abs(c_pitch), c_yaw / abs(c_pitch)
            elif abs(c_yaw) > abs(c_pitch):
                c_pitch, c_yaw = c_pitch / abs(c_yaw), c_yaw / abs(c_yaw)
            # Controls
            controls.pitch, controls.yaw = c_pitch, c_yaw
            controls.throttle = 1.0
            # Prepare for jump
            if my_car.has_wheel_contact == True:
                if get_angle(aerial_front_jump, car_velocity) >= math.pi / 2:
                    controls.throttle = -1
                elif self.jumping < 0:
                    self.jumping = 0.2
            # Double jump
            if self.jumping < 0 and aerial_intersection_jump + get_angle(aerial_front, aerial_front_jump) / 5.5 < aerial_intersection and get_angle(aerial_front_jump, aerial_front) <= math.pi / 4 and my_car.double_jumped == False:
                self.jump_flip = False
                self.jumping = 2/60
            if get_angle(car_direction, aerial_front) <= math.pi / 4:
                controls.boost = True
            if my_car.has_wheel_contact == True:
                controls.steer = steer_toward_target(my_car, Vec3(predict_ball(aerial_intersection).physics.location))
            # Prepare for frame-perfect hit
            if my_car.has_wheel_contact == False:
                if ((car_location + car_velocity / 30) - (ball_location + ball_velocity / 30)).length() <= 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() > 127.02 + self.ball_size_setting:
                    self.jumping = -1/60
                elif (car_location - ball_location).length() > 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() <= 127.02 + self.ball_size_setting:
                    self.jump_flip = True
                    self.jumping = 2/60
                    controls.pitch = -flip_value(math.cos(get_angle(dir_convert(Vec3(car_direction.x, car_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0)))))
                    controls.yaw = -flip_value(math.cos(get_angle(dir_convert(Vec3(side_direction.x, side_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0))))) * sign(roof_direction.z)
                    controls.roll = 0
            return ball_location
        # Carry & flick
        def carry_flick():
            bp = ball_location + ball_velocity * ball_bounce + Vec3(0, 0, packet.game_info.world_gravity_z / 2) * ball_bounce**2
            if surface_pos(bp, self.dropshot).z == 0:
                sv = ball_velocity
                bp = bp + Vec3(sv.y, -sv.x, 0) * safe_div(Vec3(sv.y, -sv.x, 0).length()) * 30 * steer_toward_target(my_car, send_location) * sign(math.pi / 2 - get_angle(car_velocity, car_direction))
            tl = bp
            controls.steer = steer_toward_target(my_car, tl)
            controls.throttle = sign(math.pi / 2 - get_angle(tl - car_location, car_direction)) * sign((surface_pos(car_location, self.dropshot) - surface_pos(tl, self.dropshot)).length() * safe_div(car_velocity.length()) - ball_bounce)
            controls.boost = controls.throttle > 0 and sign(math.pi / 2 - get_angle(car_velocity, car_direction)) >= 0
            if my_car.has_wheel_contact == False:
                controls.boost = False
            if nearest_enemy != None and random.randint(1, 100) >= (car_location - Vec3(nearest_enemy.physics.location)).length() * safe_div((car_velocity - Vec3(nearest_enemy.physics.velocity)).length() * clamp(math.cos(get_angle(Vec3(nearest_enemy.physics.location) - car_location, car_velocity - Vec3(nearest_enemy.physics.velocity))), 0.1, 1)) * 100 and my_car.has_wheel_contact == True and (surface_pos(ball_location, self.dropshot) - surface_pos(car_location, self.dropshot)).length() <= 70 and (surface_pos(ball_location, self.dropshot) - ball_location).length() <= 150:
                self.jumping = 25 / 60
                self.jump_flip = False
            # Determine the flick direction
            if my_car.has_wheel_contact == False and self.jumping < 13.5 / 60:
                self.jump_flip = True
                controls.pitch = random.randint(-1, 1)
                controls.yaw = random.randint(-1, 1)
                angle = 45 + random.randint(0, 3) * 90
                controls.pitch = math.sin(angle / 180 * math.pi)
                controls.yaw = math.cos(angle / 180 * math.pi)
            return tl
        # Anti-flick
        def anti_flick():
            tl = ball_location + (dir_convert(ball_velocity) * (1 - get_angle(ball_velocity, ball_location + send_location) / math.pi) + dir_convert(-send_location - ball_location) * get_angle(ball_velocity, ball_location + send_location) / math.pi) * ((ball_location - send_location).length() / 2 + car_velocity.length() * math.sin(get_angle(car_velocity, ball_velocity) / 2)) + Vec3(sign(car_location.x - mid_location.x) * get_angle(car_velocity, ball_velocity) * 300, 0, 0)
            controls.throttle = sign(math.pi / 2 - get_angle(car_direction, car_velocity)) * -sign(car_velocity.length() - ball_velocity.length() * (car_location + send_location).length() * safe_div((ball_location + send_location).length()) * safe_div(clamp(math.cos(get_angle(car_velocity, ball_velocity)), 0, 1)))
            controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Jump to gain power on the hit
        def power_shot():
            # Shorten
            intersectionM = intersect_time_x(packet.game_info.seconds_elapsed, ball_prediction, car_location, clamp(car_velocity.length(), 1410, 2300), max_jump_height(-packet.game_info.world_gravity_z, False), (self.ball_size_setting + 41.095), mid_location, self.dropshot, True, my_car.boost, self.boost_strength_setting, packet)
            intersectionN = nearest_intersection(packet.game_info.seconds_elapsed, car_velocity.length(), ball_prediction, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), (self.ball_size_setting + 41.095), mid_location, self.dropshot, True, packet)
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location * sign((ball_location + send_location).length() - (car_location + send_location).length())) * (self.ball_size_setting + 41.095) * sign((ball_location + send_location).length() - (car_location + send_location).length())
            disparity = (bp - surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), self.dropshot), self.dropshot))
            # Throttle
            if self.dropshot:
                if intersection == 0:
                    controls.throttle = 1
                else:
                    if sign(max_jump_height(-packet.game_info.world_gravity_z, False) - disparity) == 1 or intersection > intersectionM:
                        controls.throttle = 1
                    else:
                        controls.throttle = sign(get_angle(car_direction, car_velocity) - math.pi / 2)
            else:
                if intersection == 0:
                    controls.throttle = 1
                else:
                    if sign(max_jump_height(-packet.game_info.world_gravity_z, False) - disparity) == 1 or intersection > intersectionM:
                        controls.throttle = sign(math.pi / 2 - get_angle(car_direction, tl - car_location))
                    else:
                        controls.throttle = sign(get_angle(car_direction, tl - car_location) - math.pi / 2)
            # Stopping to block
            jt, ja = jump_time(disparity, False)
            trav_d = car_location - Vec3(predict_ball(intersectionN).physics.location)
            stop_cond = trav_d.length() * safe_div(car_velocity.length()) < intersectionN and get_angle(car_velocity, -trav_d) < math.pi / 2 and get_angle(car_velocity, -trav_d) > intersectionN
            if stop_cond:
                controls.throttle = sign(get_angle(car_direction, trav_d) - math.pi)
            controls.boost = (abs(steer_toward_target(my_car, tl)) <= 0.1 or (car_location - tl).length() >= 225000 / 99 * math.sin(get_angle(car_direction, tl - car_location) / 2) and get_angle(car_direction, tl - car_location) < math.pi / 2) and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and ((surface_pos(car_location, self.dropshot) - surface_pos_twox(Vec3(predict_ball(intersection).physics.location), car_location, max_jump_height(-packet.game_info.world_gravity_z, False), self.dropshot)).length() * safe_div(intersection) >= 1410 or disparity <= max_jump_height(-packet.game_info.world_gravity_z, False) - disparity)
            # Jumping
            jump_hold = clamp(intersection - 2 / 60, 2/60, 0.2)
            if (tl - bp).length() <= 100:
                jump_hold = 2 / 60
            # First jump
            if intersection > 0 and my_car.has_wheel_contact == True and self.jumping < 0 and (((intersection <= jt or (ball_location - car_location).length() <= 0.4 * (ball_velocity - car_velocity).length() + self.ball_size_setting) and (abs(steer_toward_target(my_car, tl)) <= 0.1 or (car_location + car_velocity * 0.5 - tl).length() <= 127.02)) or (stop_cond and get_angle(car_velocity, ball_velocity) <= math.pi / 2 and (ball_location - car_location).length() <= 0.4 * (ball_velocity - car_velocity).length() + self.ball_size_setting)) and not (nearest_enemy is not None and disparity <= 120 and get_angle(tl - car_location, Vec3(nearest_enemy.physics.location) - tl) <= math.pi / 6 and nearest_enemy.has_wheel_contact == True):
                self.jumping = jump_hold
            # Speed-flip
            if ball_location.x == 0 and ball_location.y == 0 and get_angle(tl - car_location, car_velocity) <= 0.1 and car_velocity.length() >= 800 and car_velocity.length() <= 2200 and controls.boost == True and (tl - car_location).length() * safe_div(car_velocity.length()) > 2 and my_car.boost >= 10 and surface_pos(car_location, self.dropshot).z == 0:
                self.jumping = -1 / 60
                override = self.speed_flip(packet, pref_sign(car_location.x * sign(0.5 - self.team), random.choice([-1, 1])))
            # Prepare for frame-perfect hit
            if ((car_location + car_velocity / 30) - (ball_location + ball_velocity / 30)).length() <= 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() > 127.02 + self.ball_size_setting and not (disparity <= 120 and get_angle(tl - car_location, Vec3(nearest_enemy.physics.location) - tl) <= math.pi / 6 and nearest_enemy is not None and nearest_enemy.has_wheel_contact == True):
                self.jumping = -1/60
            # The power hit
            elif my_car.has_wheel_contact == False and self.jumping < 0:
                if (car_location - ball_location).length() > 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() <= 127.02 + self.ball_size_setting:
                    self.jumping = -1 / 60
                    override = self.generic_flip(packet, -flip_value(math.cos(get_angle(dir_convert(Vec3(side_direction.x, side_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0))))) * sign(roof_direction.z), -flip_value(math.cos(get_angle(dir_convert(Vec3(car_direction.x, car_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0))))), 0, 0, 0.8)
                controls.boost = False
                controls.throttle = 0
            if get_angle(tl - car_location, car_velocity) > math.pi / 2 and sign(steer_toward_target(my_car, tl)) != sign(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))):
                controls.steer = steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))
            else:
                controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Pace
        def pace():
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * (self.ball_size_setting + 41.095)
            disparity = (bp - surface_pos(bp, self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, bp, self.dropshot))
            
            if intersection == 0:
                controls.throttle = 1
            else:
                if sign(max_jump_height(-packet.game_info.world_gravity_z, False) - disparity) == 1 or intersection > intersection:
                    controls.throttle = sign(math.pi / 2 - get_angle(car_direction, tl - car_location))
                else:
                    controls.throttle = sign(get_angle(car_direction, tl - car_location) - math.pi / 2)
                    
            controls.boost = abs(steer_toward_target(my_car, tl)) <= 0.1 and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and (surface_pos(car_location, self.dropshot) - surface_pos(Vec3(predict_ball(intersection).physics.location), self.dropshot)).length() * safe_div(intersection) >= 1410
            if car_velocity.length() >= 800 and car_velocity.length() <= 2200 and controls.boost == True and my_car.boost >= 10:
                self.jumping = -1 / 60
                override = self.speed_flip(packet, pref_sign(car_location.x, random.choice([-1, 1])))
            return tl
        # Jump to reach the ball
        def reach():
            # Shorten
            intersectionM = intersect_time_x(packet.game_info.seconds_elapsed, ball_prediction, car_location, clamp(car_velocity.length(), 1410, 2300), max_jump_height(-packet.game_info.world_gravity_z, True), self.ball_size_setting, mid_location, self.dropshot, True, my_car.boost, self.boost_strength_setting, packet)
            intersectionN = nearest_intersection(packet.game_info.seconds_elapsed, car_velocity.length(), ball_prediction, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.ball_size_setting, mid_location, self.dropshot, True, packet)
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * self.ball_size_setting
            disparity = (bp - surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot), self.dropshot))
            jt, ja = jump_time(disparity, True)
            # Throttle
            if self.dropshot:
                if intersection == 0:
                    controls.throttle = 1
                else:
                    if sign(max_jump_height(-packet.game_info.world_gravity_z, True) - disparity) == 1 or intersection > intersectionM:
                        controls.throttle = 1
                    else:
                        controls.throttle = sign(get_angle(car_direction, car_velocity) - math.pi / 2)
            else:
                if intersection == 0:
                    controls.throttle = 1
                else:
                    if sign(max_jump_height(-packet.game_info.world_gravity_z, True) - disparity) == 1 or intersection > intersectionM:
                        controls.throttle = 1
                    else:
                        controls.throttle = sign(get_angle(car_direction, car_velocity) - math.pi / 2)
            # Stopping to block
            trav_d = car_location - Vec3(predict_ball(intersectionN).physics.location)
            stop_cond = trav_d.length() * safe_div(car_velocity.length()) < intersectionN and get_angle(car_velocity, -trav_d) < math.pi / 2 and get_angle(car_velocity, -trav_d) > intersectionN
            if stop_cond:
                controls.throttle = sign(get_angle(car_direction, trav_d) - math.pi)
            controls.boost = abs(steer_toward_target(my_car, tl)) <= 0.1 and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and (surface_pos(car_location, self.dropshot) - surface_pos_twox(Vec3(predict_ball(intersectionM).physics.location), car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot)).length() * safe_div(intersectionM) >= 1410
            
            # Jumping
            jump_hold = 0.2 + bool(ja == 2) * 13 / 60
            if intersection > 0 and my_car.has_wheel_contact == True and self.jumping < 0 and intersection <= jt and abs(steer_toward_target(my_car, tl)) <= 0.1 and (tl - bp).length() >= 100:
                self.jump_flip = False
                self.jumping = jump_hold
            if my_car.has_wheel_contact == False and get_angle(car_velocity, tl - car_location) < math.pi / 2:
                future_pos = car_location + car_velocity * intersection - Vec3(0, 0, 325) * intersection**2
                controls.pitch, controls.yaw = aerial_control(dir_convert(bp - future_pos), car_rotation, 0.8, True)
                if not my_car.double_jumped:
                    controls.pitch = 0
            if get_angle(tl - car_location, car_velocity) > math.pi / 2 and sign(steer_toward_target(my_car, tl)) != sign(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))):
                controls.steer = steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))
            else:
                controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Retreat
        def retreat(emergency):
            # The target to retreat to
            if get_angle(Vec3(predict_ball(intersection).physics.location) - car_location, send_location - car_location) > math.pi / 2:
                togo_x = predict_ball(intersection).physics.location.x + pref_sign(car_location.x - predict_ball(intersection).physics.location.x, random.choice([-1, 1])) * clamp(car_velocity.length() * 1.5 / 2.3, 400, 1500)
                r_x = clamp(abs(togo_x) * sign(togo_x) * sign(car_location.x), 910, math.inf) * sign(car_location.x)
                tl = wall_transition_path(car_location, Vec3(r_x, -send_location.y / abs(send_location.y) * abs(abs(send_location.y) - car_velocity.length() * 0.75), 0), self.dropshot)
            else:
                tl = wall_transition_path(car_location, Vec3(clamp(car_location.x, -910, 910), -send_location.y, 0), self.dropshot)
            # Controls
            controls.boost = not my_car.jumped and emergency and car_velocity.length() < 2290 and get_angle(car_direction, tl - car_location) < math.pi / 2
            controls.throttle = sign(math.pi / 2 - get_angle(car_velocity, car_direction))
            controls.steer = steer_toward_target(my_car, tl)
            # Flips
            if my_car.has_wheel_contact == True and (car_location - tl).length() > car_velocity.length() * 0.2 + (car_velocity.length() + 292) * 1.5:
                if (my_car.boost == 0 or not emergency) and get_angle(tl - car_location, car_velocity) <= 0.1 and car_velocity.length() > 1000 and surface_pos(car_location, self.dropshot).z == 0 and get_angle(car_velocity, car_direction) <= math.pi / 2:
                    self.jumping = -1 / 60
                    override = self.generic_flip(packet, 0, -1, 8/60, 1/60, 0.8)
                elif abs(steer_toward_target(my_car, tl)) < 0.2 and get_angle(car_velocity, car_direction) > math.pi / 2:
                    self.jumping = -1 / 60
                    override = self.reverse_flip(packet, 1)
            # Jump off the back wall
            if my_car.has_wheel_contact == True and surface_pos(car_location, self.dropshot).y == sign(send_location.y):
                self.jump_flip = False
                self.jumping = 0.2 + 13 / 60
            # Speed-flip
            if False and car_velocity.length() >= 800 and car_velocity.length() <= 1400 and controls.boost == True and my_car.boost >= 10 and (car_location - tl).length() > car_velocity.length() * 0.2 + (car_velocity.length() + 292) * 1:
                self.jumping = -1 / 60
                override = self.speed_flip(packet, pref_sign(car_location.x, random.choice([-1, 1])))
            return tl
        # Catch
        def catch():
            bounce = next_bounce(packet.game_info.seconds_elapsed, ball_prediction, car_location, 2300, 30 + car_velocity.length() / 70, mid_location, self.dropshot, packet)
            tl = Vec3(predict_ball(bounce).physics.location)
            tl = tl - dir_to_point(tl, mid_location) * (30 + car_velocity.length() / 70)
            # Throttle
            if bounce == 0:
                controls.throttle = 1
            else:
                if (car_location - tl).length() / bounce > car_velocity.length():
                    controls.throttle = pref_sign(math.pi / 2 - get_angle(car_direction, car_velocity), 1)
                    controls.boost = (car_velocity.length() > 1000 and pref_sign(math.pi / 2 - get_angle(car_direction, car_velocity), 1) == 1)
                else:
                    controls.throttle = 0
            # Flick
            if Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0).length() <= 50 and abs(ball_location.z - car_location.z) <= 140:
                if nearest_et <= 0.5:
                    controls.jump = True
            controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Nudge
        def nudge():
            return 1
        # Setup shot
        def setup(cl, tp, hp, slowdown):
            k = get_angle(cl - tp, tp - hp)
            tl = setup_curve(cl, tp, hp)
            if surface_pos(car_location, self.dropshot).y == mid_location.y:
                tl = Vec3(car_location.x, car_location.y, 0)
            controls.steer = steer_toward_target(my_car, tl)
            if slowdown:
                controls.throttle = sign(get_angle(car_direction, car_velocity) - math.pi / 2)
                controls.boost = False
                self.no_hold_off_time = 0
            return tl
        '''
        Behaviours
        '''
        # 1v1 (Soccer)
        def duel():
            mode, mode_comp = "", ""
            sp = Vec3(predict_ball(intersection - self.ball_size_setting * safe_div(car_velocity.length())).physics.location)
            cond_hold = abs(sp.x) > (893 - self.ball_size_setting * 2 + abs(sp.y + send_location.y)) and predict_ball(5).physics.location.x * sign(sp.x) <= (893 - self.ball_size_setting * 2 + abs(sp.y + send_location.y))
            e_balling = nearest_enemy is not None and (Vec3(nearest_enemy.physics.velocity) - ball_velocity).length() < 100 and (Vec3(nearest_enemy.physics.location) - ball_location).length() <= 500
            e_carrying = nearest_enemy is not None and ((surface_pos(ball_location, self.dropshot) - surface_pos(Vec3(nearest_enemy.physics.location), self.dropshot)).length() <= 90 and (surface_pos(ball_location, self.dropshot) - ball_location).length() <= 150)
            # Fundamental mode
            '''
            elif ((nearest_enemy == None or nearest_ft <= ball_bounce <= nearest_et + 0.3 + bool(nearest_enemy.has_wheel_contact == False) / 2) or ((surface_pos(ball_location, self.dropshot) - surface_pos(car_location, self.dropshot)).length() <= 90 and (surface_pos(ball_location, self.dropshot) - ball_location).length() <= 150)) and surface_pos(ball_location + ball_velocity * ball_bounce + Vec3(0, 0, packet.game_info.world_gravity_z / 2) * ball_bounce**2, self.dropshot).z == 0 and ball_location.z > 100:
                mode = "Carry & flick"
            '''
            if e_carrying and (car_location - send_location).length() < (Vec3(nearest_enemy.physics.location) - send_location).length():
                mode = "Anti-flick"
            elif not packet.game_info.is_kickoff_pause and nearest_enemy is not None and will_intersect(Vec3(nearest_enemy.physics.location) - ball_location, Vec3(nearest_enemy.physics.velocity) - ball_velocity, self.ball_size_setting + 65.755) and sign(ball_location.y + (Vec3(nearest_enemy.physics.velocity).y * 1.25 - ball_velocity.y * 0.25) * predict_surface_bounce(ball_location, (Vec3(nearest_enemy.physics.velocity) * 1.5 - ball_velocity * 0.5), self.ball_size_setting, 650) - car_location.y) != sign(send_location.y) and (ball_location - Vec3(nearest_enemy.physics.location)).length() * safe_div((ball_velocity - Vec3(nearest_enemy.physics.velocity)).length()) < predict_surface_bounce(Vec3(nearest_enemy.physics.location), Vec3(nearest_enemy.physics.velocity), 20, -packet.game_info.world_gravity_z) and nearest_enemy.has_wheel_contact == False and nearest_ft + 0.2 > nearest_et and my_car.has_wheel_contact == True:
                mode = "Retreat_E"
            elif (not (emergency != None and sign(emergency.physics.location.y) == sign(send_location.y)) or nearest_enemy == None or (nearest_et > nearest_ft and get_angle(Vec3(nearest_enemy.physics.location) - ball_location, mid_location - ball_location) >= math.pi / 2)) and get_angle(Vec3(predict_ball(intersection).physics.location) - car_location, send_location - car_location) <= math.pi / 2 and not e_balling and (sign(car_velocity.y) * sign(send_location.y) >= 0 or nearest_et >= nearest_ft) or cond_hold or car_location.y * sign(send_location.y) <= car_velocity.length() * 0.75 - 5120 or packet.game_info.is_kickoff_pause:
                if (nearest_et <= 1.5 or emergency != None and sign(emergency.physics.location.y) == -sign(send_location.y)) and predict_ball(intersection).physics.location.z > max_jump_height(-packet.game_info.world_gravity_z, False) / 10 * 9:
                    mode = "Reach"
                else:
                    mode = "Power shot"
                if nearest_et > nearest_ft and aerial_intersection > 0 and (Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos_twox(Vec3(predict_ball(aerial_intersection).physics.location), self.last_surface, math.inf, self.dropshot)).length() > clamp(max_jump_height(-packet.game_info.world_gravity_z, mode == "Reach"), 0, 300 + 200 * bool(mode == "Reach")):
                    mode = "Aerial"
            else:
                mode = "Retreat"
                if nearest_et < nearest_ft:
                    mode += "_E"
            tl = get_modes(mode)
            # Prepare the jump time variable
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * (self.ball_size_setting + 41.095 * bool(mode == "Power shot"))
            disparity = (bp - surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, bool(mode == "Reach")), self.dropshot)).length()
            jt, ja = jump_time(disparity, mode == "Reach")
            # Other variables
            boost_pad = find_boost_pad(tl)
            cond_hold = abs(sp.x) > (893 - self.ball_size_setting * 2 + abs(sp.y - send_location.y)) and predict_ball(5).physics.location.x * sign(sp.x) <= (893 - self.ball_size_setting * 2 + abs(sp.y - send_location.y))
            d_to_boost_goal = (boost_pad - car_location).length() + (boost_pad + send_location).length()
            # Complimentary mode
            if nearest_enemy is not None and will_intersect(Vec3(nearest_enemy.physics.location) - ball_location, Vec3(nearest_enemy.physics.velocity) - ball_velocity, self.ball_size_setting + 65.755) and sign(ball_location.y + (Vec3(nearest_enemy.physics.velocity).y * 1.25 - ball_velocity.y * 0.25) * predict_surface_bounce(ball_location, (Vec3(nearest_enemy.physics.velocity) * 1.25 - ball_velocity * 0.25), self.ball_size_setting, 650) - car_location.y) == sign(send_location.y) and (ball_location - Vec3(nearest_enemy.physics.location)).length() * safe_div((ball_velocity - Vec3(nearest_enemy.physics.velocity)).length()) < predict_surface_bounce(Vec3(nearest_enemy.physics.location), Vec3(nearest_enemy.physics.velocity), 20, -packet.game_info.world_gravity_z) and nearest_enemy.has_wheel_contact == False and nearest_ft + 0.2 > nearest_et and my_car.has_wheel_contact == True and (surface_pos_twox(freefall(ball_location, (Vec3(nearest_enemy.physics.velocity) * 1.5 - ball_velocity * 0.5), -packet.game_info.world_gravity_z, predict_surface_bounce(ball_location, (Vec3(nearest_enemy.physics.velocity) * 1.5 - ball_velocity * 0.5), self.ball_size_setting, 650)), car_location, max_jump_height(-packet.game_info.world_gravity_z, mode == "Reach"), self.dropshot) - surface_pos(car_location, self.dropshot)).length() * safe_div(car_velocity.length()) <= predict_surface_bounce(ball_location, (Vec3(nearest_enemy.physics.velocity) * 1.5 - ball_velocity * 0.5), self.ball_size_setting, 650):
                mode_comp = "Hold off"
            elif mode not in ["Aerial", "Carry & flick"] and ((my_car.has_wheel_contact == False and get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) <= math.pi / 2) or get_angle(car_direction, car_velocity) > math.pi / 8):
                mode_comp = "Recovery"
            elif False and not emergency and mode not in ["Retreat_E", "Aerial"] and intersection > jt + get_angle(car_velocity, ball_location - car_location) + 1 and (my_car.boost / 100 * 3 + jt < nearest_ft <= nearest_et > ((boost_pad - car_location).length() + (boost_pad - tl).length()) / clamp(car_velocity.length() + 292, 1410, 2300) + 1 or (nearest_et < nearest_ft and (-send_location - Vec3(predict_ball(intersection).physics.location)).length() > d_to_boost_goal)):
                mode_comp = "Refuel"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and nearest_et < nearest_ft - 0.3 and (car_location - ball_location).length() * safe_div((car_velocity - ball_velocity).length()) >= get_angle(car_direction, ball_location - car_location) and intersection > jt + get_angle(car_velocity, ball_location - car_location):
                mode_comp = "Shadow"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and ball_location.x * ball_location.y != 0 and (nearest_et > nearest_ft + 0.2 or (cond_hold)) and (car_location - ball_location).length() * safe_div((car_velocity - ball_velocity).length()) >= get_angle(car_direction, ball_location - car_location) and intersection > jt + get_angle(car_velocity, ball_location - car_location):
                if cond_hold:
                    mode_comp = "Hold off"
                else:
                    mode_comp = "Setup"
            return tl, [mode, mode_comp]
        # 2v2 (Soccer)
        def doubles():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        # 3v3 (Soccer)
        def standard():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        # 4v4 (Soccer)
        def chaos():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        # 1v1 (Dropshot)
        def duel_dropshot():
            mode, mode_comp = "", ""
            if aerial_intersection > 0 and ((Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos_twox(Vec3(predict_ball(aerial_intersection).physics.location), car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, True) or (nearest_enemy is None or nearest_enemy.has_wheel_contact == False and nearest_friendly == my_car and (Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos(Vec3(predict_ball(aerial_intersection).physics.location), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, False) and (nearest_enemy is None or nearest_et > aerial_intersection + get_angle(car_direction, aerial_front) / 6 and False))):
                mode = "Aerial"
            else:
                if (nearest_et <= 1.5 and predict_ball(intersection).physics.location.z > max_jump_height(-packet.game_info.world_gravity_z, False)) or (sign(predict_ball(intersection).physics.location.y) != sign(send_location.y)):
                    mode = "Reach"
                else:
                    mode = "Power shot"
            if mode != "Aerial" and ((my_car.has_wheel_contact == False and get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) <= math.pi / 2) or get_angle(car_direction, car_velocity) > math.pi / 8):
                mode_comp = "Recovery"
            '''
            if nearest_et > nearest_ft + 0.2 and packet.game_ball.latest_touch.team != self.team or sign(predict_ball(intersection).physics.location.y) != sign(send_location.y):
                if (nearest_et <= 1.5 and predict_ball(intersection).physics.location.z > max_jump_height(-packet.game_info.world_gravity_z, False) * 9 / 10) or (sign(predict_ball(intersection).physics.location.y) != sign(send_location.y)):
                    if aerial_intersection > 0 and 500 < (Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos(Vec3(predict_ball(aerial_intersection).physics.location), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, True):
                        mode = "Aerial"
                    else:
                        mode = "Reach"
                else:
                    if aerial_intersection > 0 and 300 < (Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos(Vec3(predict_ball(aerial_intersection).physics.location), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, False):
                        mode = "Aerial"
                    else:
                        mode = "Power shot"
            else:
                mode = "Retreat"
            # Prepare the jump time variable
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * (self.ball_size_setting + ((self.ball_size_setting + 41.095) - self.ball_size_setting) * bool(mode == "Power shot"))
            disparity = (bp - surface_pos_twox(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, bool(mode == "Reach")), self.dropshot)).length()
            jt, ja = jump_time(disparity, mode == "Reach")
            # Complimentary mode
            if mode != "Aerial" and ((my_car.has_wheel_contact == False and get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) <= math.pi / 2) or get_angle(car_direction, car_velocity) > math.pi / 8):
                mode_comp = "Recovery"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and nearest_et > nearest_ft + 0.2 and intersection > jt + get_angle(car_velocity, ball_location - car_location) and sign(ball_location.y + ball_velocity.y * nearest_ft) == -sign(send_location.y) and packet.game_ball.latest_touch.team == self.team:
                mode_comp = "Setup"
            '''
            return None, [mode, mode_comp]
        # 2v2 (Dropshot)
        def doubles_dropshot():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        # 3v3 (Dropshot)
        def standard_dropshot():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        # 4v4 (Dropshot)
        def chaos_dropshot():
            mode, mode_comp = "", ""
            return tl, [mode, mode_comp]
        def get_modes(mode):
            try:
                if mode == "Read hit":
                    target_location = read_hit()
                elif mode == "Aerial":
                    target_location = aerial()
                elif mode == "Reach":
                    target_location = reach()
                elif mode == "Power shot":
                    target_location = power_shot()
                elif mode == "Retreat":
                    target_location = retreat(False)
                elif mode == "Retreat_E":
                    target_location = retreat(True)
                elif mode == "Tight":
                    target_location = tight_shots()
                elif mode == "Catch":
                    target_location = catch()
                elif mode == "Carry & flick":
                    target_location = carry_flick()
                elif mode == "Anti-flick":
                    target_location = anti_flick()
            except UnboundLocalError:
                print("The mode '" + mode + "' doesn't exist!");
                target_location = power_shot()
            return target_location
        def get_modes_comp(mode_comp, target_location):
            ntarget_location = target_location
            if mode_comp == "Recovery":
                recovery()
            elif mode_comp == "Setup":
                ntarget_location = setup(car_location, target_location, mid_location, False)
            elif mode_comp == "Shadow":
                ntarget_location = setup(car_location, target_location, (ball_location + ball_velocity * nearest_et) * 2 + mid_location, False)
            elif mode_comp == "Refuel":
                ntarget_location = refuel()
            elif mode_comp == "Hold off":
                ntarget_location = setup(car_location, target_location, mid_location, True)
            return ntarget_location
        # Experimental Behaviours
        def behaviour_x():
            return "Catch", ""
        # Variables
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        car_rotation = my_car.physics.rotation
        car_direction = Vec3(math.cos(car_rotation.yaw) * math.cos(car_rotation.pitch), math.sin(car_rotation.yaw) * math.cos(car_rotation.pitch), math.sin(car_rotation.pitch))
        roof_direction = Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(car_rotation.roll) + math.sin(car_rotation.yaw) * math.sin(car_rotation.roll), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(car_rotation.roll) - math.cos(car_rotation.yaw) * math.sin(car_rotation.roll), math.cos(car_rotation.roll) * math.cos(car_rotation.pitch))
        side_direction = Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * -math.sin(car_rotation.roll) + math.sin(car_rotation.yaw) * math.cos(car_rotation.roll), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * -math.sin(car_rotation.roll) - math.cos(car_rotation.yaw) * math.cos(car_rotation.roll), -math.sin(car_rotation.roll) * math.cos(car_rotation.pitch))
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        ball_prediction = self.get_ball_prediction_struct()
        ball_bounce = predict_surface_bounce(ball_location, ball_velocity, self.ball_size_setting, 650)
        send_location, mid_location = get_send()
        number_friendly, number_enemy = player_count()
        nearest_friendly, nearest_ft = read_players(400, True)
        role_in_team = distance_order()
        nearest_enemy, nearest_et = read_players(400, False)
        angle_disparity = get_angle(Vec3(-800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0))
        angle_comparison = get_angle(Vec3(-800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(car_direction.x, car_direction.y, 0)) + get_angle(Vec3(800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(car_direction.x, car_direction.y, 0))
        if my_car.has_wheel_contact:
            self.last_surface = car_location
        package = ["", ""]
        emergency = predict_future_goal(ball_prediction)
        override = None
        if my_car.jumped == False:
            jump_gain = 292
        else:
            jump_gain = 0
        aerial_front, aerial_intersection = aerial_dir(car_location, car_velocity + roof_direction * jump_gain, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, 1, 1, packet)
        intersection = intersect_time(packet.game_info.seconds_elapsed, ball_prediction, car_location, car_velocity.length(), math.inf, self.ball_size_setting, send_location, self.dropshot, True, my_car.boost, packet)
        if packet.game_info.is_kickoff_pause == True:
            self.kickoff = -packet.game_ball.latest_touch.time_seconds
        if packet.game_ball.latest_touch != -self.kickoff:
            self.kickoff = packet.game_ball.latest_touch.time_seconds
        if self.prev_rot:
            pitch_velocity, yaw_velocity = get_angular_velocity(self.prev_rot, car_direction)
        else:
            pitch_velocity, yaw_velocity = 0, 0

        controls = SimpleControllerState()
        # Modes and Team size
        target_location = None
        if False:
            target_location, package = behaviour_x()
        elif self.dropshot == True:
            if number_friendly >= 1:
                target_location, package = duel_dropshot()
            elif number_friendly == 2:
                target_location, package = doubles_dropshot()
            elif number_friendly == 3:
                target_location, package = standard_dropshot()
            elif number_friendly >= 4:
                target_location, package = chaos_dropshot()
        else:
            if number_friendly >= 1:
                target_location, package = duel()
            elif number_friendly == 2:
                target_location, package = doubles()
            elif number_friendly == 3:
                target_location, package = standard()
            elif number_friendly >= 4:
                target_location, package = chaos()
        mode, mode_comp = package[0], package[1]
        if target_location == None:
            target_location = get_modes(mode)
        target_location = get_modes_comp(mode_comp, target_location)
        avoid_bump()
        '''
        if self.aerial_situation == "Free" and mode == "Aerial":
            self.send_comm(True, self.index)
            self.aerial_situation = "Committing"
        elif self.aerial_situation == "Committing" and mode != "Aerial":
            self.send_comm(False, self.index)
            self.aerial_situation = "Free"
        '''
        
        if self.jumping > -1/60:
            self.jumping -= 1/60
            if self.jumping > 12/60 and self.jumping < 14/60:
                controls.jump = False
                self.jumping = 2/60
            elif self.jumping > 0:
                if self.jump_flip == False:
                    controls.roll = 0
                    controls.yaw = 0
                    controls.pitch = 0
                controls.jump = True
        # Hold off to save boost
        if self.no_hold_off_time <= 1 / 60 and mode in ["Power shot", "Reach", "Carry & flick"]:
            controls.boost = False
        self.no_hold_off_time += 1/60

        self.renderer.draw_line_3d(car_location, surface_pos(car_location, self.dropshot), self.renderer.white())
        self.renderer.draw_string_3d(car_location, 1, 1, mode + " (" + mode_comp + ")", self.renderer.white())
        if self.dropshot:
            for i in range(140):
                self.renderer.draw_string_3d(get_pos(i), 1, 1, str(i), self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_rect_3d(send_location, 8, 8, True, self.renderer.green(), centered=True)
        # The bot's personality in chat
        if my_car.is_demolished == True:
            self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Compliments_Thanks)
        self.prev_rot = car_direction
        # Return the controls
        if override:
            return override
        else:
            return controls

    def single_jump(self, packet, dir_x, dir_y, delay, jump_endurance, halt):
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        self.active_sequence = Sequence([
            ControlStep(duration=jump_endurance, controls=SimpleControllerState(jump = True)),
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

    def generic_flip(self, packet, dir_x, dir_y, delay, jump_endurance, halt):
        if delay == 0:
            self.active_sequence = Sequence([
                ControlStep(duration=0.05, controls=SimpleControllerState(jump = True, pitch = dir_y, yaw = dir_x)),
                ControlStep(duration=halt, controls=SimpleControllerState()),
            ])
        elif jump_endurance == 0:
            self.active_sequence = Sequence([
                ControlStep(duration=delay, controls=SimpleControllerState(jump = False)),
                ControlStep(duration=0.05, controls=SimpleControllerState(jump = True, pitch = dir_y, yaw = dir_x)),
                ControlStep(duration=halt, controls=SimpleControllerState()),
            ])
        else:
            self.active_sequence = Sequence([
                ControlStep(duration=jump_endurance, controls=SimpleControllerState(jump = True)),
                ControlStep(duration=delay, controls=SimpleControllerState(jump = False)),
                ControlStep(duration=0.05, controls=SimpleControllerState(jump = True, pitch = dir_y, yaw = dir_x)),
                ControlStep(duration=halt, controls=SimpleControllerState()),
            ])

        return self.active_sequence.tick(packet)
        
    def reverse_flip(self, packet, flip_dir):
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True, throttle=-1)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, throttle=-1)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=flip_dir, throttle=-1)),
            ControlStep(duration=0.25, controls=SimpleControllerState(jump=False, pitch=-flip_dir, throttle=1)),
            ControlStep(duration=0.3, controls=SimpleControllerState(roll=random.choice([-1, 1]), pitch=-flip_dir, throttle=1)),
            ControlStep(duration=0.05, controls=SimpleControllerState(throttle=1)),
        ])

        return self.active_sequence.tick(packet)
