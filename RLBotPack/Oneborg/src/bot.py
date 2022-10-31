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
        # Steer to improve reversing
        def fix_reversing(val):
            return val * clamp(math.pi - get_angle(car_direction, car_velocity), 0, 1)
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
                o_pos = Vec3(other_p.physics.location)
                if o_pos.z > 0:
                    o_vel = Vec3(other_p.physics.velocity)
                    offset_pos = ball_location - o_pos
                    offset_vel = ball_velocity - o_vel
                    val = (offset_pos.length() - self.ball_size_setting) * safe_div(offset_vel.length() + offset) + get_angle(offset_vel, -offset_pos)
                    if other_p.team == self.team and team_type == True:
                        if val < nearest_t:
                            nearest_t = val
                            nearest_p = other_p
                            nearest_k = (offset_vel.length() + offset) * safe_div(offset_vel.length())
                    elif other_p.team != self.team and team_type == False:
                        if val < nearest_t:
                            nearest_t = val
                            nearest_p = other_p
                            nearest_k = (offset_vel.length() + offset) * safe_div(offset_vel.length())
                    '''
                    # Read aerial hits
                    t = -(offset_pos.x * offset_vel.x + offset_pos.y * offset_vel.y + offset_pos.z * offset_vel.z) * safe_div(offset_vel.x**2 + offset_vel.y**2 + offset_vel.z**2)
                    will_hit = (offset_vel.x**2 + offset_vel.y**2 + offset_vel.z**2) * t**2 + 2 * (offset_pos.x * offset_vel.x + offset_pos.y * offset_vel.y + offset_pos.z * offset_vel.z) * t + offset_pos.x**2 + offset_pos.y**2 + offset_pos.z**2 < 125
                    '''
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
                        if my_car.has_wheel_contact == True:
                            self.jumping = 2 / 60
                        elif get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) < math.pi / 2 and (vel2 - vel).length() <= 300:
                            override = self.generic_flip(packet, -flip_value(math.cos(get_angle(dir_convert(Vec3(side_direction.x, side_direction.y, 0)), dir_convert(Vec3(packet.game_cars[i].physics.location.x - car_location.x, packet.game_cars[i].physics.location.y - car_location.y, 0))))) * sign(roof_direction.z), -flip_value(math.cos(get_angle(dir_convert(Vec3(car_direction.x, car_direction.y, 0)), dir_convert(Vec3(packet.game_cars[i].physics.location.x - car_location.x, packet.game_cars[i].physics.location.y - car_location.y, 0))))), 0, 0, 0.8)
        '''§11
        Actions
        '''
        # Try to land on a surface
        def recovery():
            # Surfaces
            sl = car_location + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(-math.pi / 2 * 1) + math.sin(car_rotation.yaw) * math.sin(-math.pi / 2 * 1), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(-math.pi / 2 * 1) - math.cos(car_rotation.yaw) * math.sin(-math.pi / 2 * 1), math.cos(-math.pi / 2 * 1) * math.cos(car_rotation.pitch))
            su = car_location + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 0) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 0), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 0) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 0), math.cos(math.pi / 2 * 0) * math.cos(car_rotation.pitch))
            sr = car_location + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 1) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 1), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 1) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 1), math.cos(math.pi / 2 * 1) * math.cos(car_rotation.pitch))
            sd = car_location + Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 2) + math.sin(car_rotation.yaw) * math.sin(math.pi / 2 * 2), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(math.pi / 2 * 2) - math.cos(car_rotation.yaw) * math.sin(math.pi / 2 * 2), math.cos(math.pi / 2 * 2) * math.cos(car_rotation.pitch))
            if (su - surface_pos(car_location, self.dropshot)).length() <= (sl - surface_pos(car_location, self.dropshot)).length() and (su - surface_pos(car_location, self.dropshot)).length() <= (sr - surface_pos(car_location, self.dropshot)).length() and (su - surface_pos(car_location, self.dropshot)).length() <= (sd - surface_pos(car_location, self.dropshot)).length():
                controls.roll = clamp(-(math.pi - abs(car_rotation.roll)) * sign(car_rotation.roll), -1, 1)
            elif (sl - surface_pos(car_location, self.dropshot)).length() <= (su - surface_pos(car_location, self.dropshot)).length() and (sl - surface_pos(car_location, self.dropshot)).length() <= (sr - surface_pos(car_location, self.dropshot)).length() and (sl - surface_pos(car_location, self.dropshot)).length() <= (sd - surface_pos(car_location, self.dropshot)).length():
                controls.roll = clamp(-car_rotation.roll - math.pi / 2, -1, 1)
            elif (sr - surface_pos(car_location, self.dropshot)).length() <= (sl - surface_pos(car_location, self.dropshot)).length() and (sr - surface_pos(car_location, self.dropshot)).length() <= (su - surface_pos(car_location, self.dropshot)).length() and (sr - surface_pos(car_location, self.dropshot)).length() <= (sd - surface_pos(car_location, self.dropshot)).length():
                controls.roll = clamp(-car_rotation.roll + math.pi / 2, -1, 1)
            elif (sd - surface_pos(car_location, self.dropshot)).length() <= (sl - surface_pos(car_location, self.dropshot)).length() and (sd - surface_pos(car_location, self.dropshot)).length() <= (su - surface_pos(car_location, self.dropshot)).length() and (sd - surface_pos(car_location, self.dropshot)).length() <= (sr - surface_pos(car_location, self.dropshot)).length():
                controls.roll = clamp(-car_rotation.roll, -1, 1)
            if my_car.has_wheel_contact == False:
                controls.pitch, controls.yaw = aerial_control(dir_convert(surface_pos(car_location + car_velocity * safe_div(car_velocity.length()), self.dropshot) - surface_pos(car_location, self.dropshot)), car_rotation, 0.5)
        # Refueling
        def refuel():
            best_pad = None
            best_score = math.inf
            for i in range(len(self.get_field_info().boost_pads)):
                pad = self.get_field_info().boost_pads[i]
                if (Vec3(pad.location) - Vec3(0, 0, 0)).length() >= 100 and (packet.game_boosts[i].is_active == True or packet.game_boosts[i].timer <= (Vec3(pad.location) - car_location).length() * safe_div(clamp(car_velocity.length(), 1410, 2300))):
                    full = pad.is_full_boost
                    if full:
                        benefit = clamp(100 - my_car.boost, 0, 100)
                    else:
                        benefit = clamp(100 - my_car.boost, 0, 12)
                    score = ((car_location - Vec3(pad.location)).length() + (target_location - Vec3(pad.location)).length() - (car_location - target_location).length()) * safe_div(benefit)
                    if score < best_score:
                        best_score = score
                        best_pad = pad
            controls.throttle = 1.0
            if best_pad:
                tl = Vec3(best_pad.location)
            else:
                tl = target_location
            controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Fly to get the ball
        def aerial():
            # Decide whether to double jump
            aerial_front_jump, aerial_intersection_jump = aerial_dir(car_location, car_velocity + roof_direction * 292, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, 1, 1, packet)
            # Controls
            controls.pitch, controls.yaw = aerial_control(aerial_front, car_rotation, 1)
            controls.throttle = 1.0
            if my_car.has_wheel_contact == True and self.jumping < 0:
                self.jumping = 0.2
            if self.jumping < 0 and aerial_intersection_jump < aerial_intersection and get_angle(aerial_front_jump, aerial_front) <= math.pi / 4 and my_car.double_jumped == False:
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
        # Fly to get the ball
        def aerial_x():
            # Decide whether to double jump
            aerial_front_jump, aerial_intersection_jump = aerial_dir(car_location, car_velocity + roof_direction * 292, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, 1, 1, packet)
            aerial_front_faster, aerial_intersection_faster = aerial_dir(car_location, car_velocity + roof_direction * 292 + car_direction * get_accel(car_velocity.length()) * safe_div(car_velocity.length()) / 60, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, math.ceil(aerial_intersection - 1), 1, packet)
            aerial_front_boost, aerial_intersection_boost = aerial_dir(car_location, car_velocity + roof_direction * 292 + car_direction * (get_accel(car_velocity.length()) + 5950 / 360) * safe_div(car_velocity.length()) / 60, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, math.ceil(aerial_intersection - 1), 1, packet)
            aerial_front_slower, aerial_intersection_slower = aerial_dir(car_location, car_velocity + roof_direction * 292 - car_direction * get_accel(-car_velocity.length()) * safe_div(car_velocity.length()) / 60, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, math.ceil(aerial_intersection - 1), 1, packet)
            aerial_front_left, aerial_intersection_left = aerial_dir(car_location, direction_offset(dir_convert(car_direction), Vec3(0, 0, 1), -math.pi / 93) * car_velocity.length() + roof_direction * 292, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, math.ceil(aerial_intersection - 1), 1, packet)
            aerial_front_right, aerial_intersection_right = aerial_dir(car_location, direction_offset(dir_convert(car_direction), Vec3(0, 0, 1), math.pi / 93) * car_velocity.length() + roof_direction * 292, packet.game_info.seconds_elapsed, ball_prediction, send_location, my_car.boost, self.ball_size_setting, self.boost_strength_setting, -packet.game_info.world_gravity_z, math.ceil(aerial_intersection - 1), 1, packet)
            # Controls
            controls.pitch, controls.yaw = aerial_control(aerial_front, car_rotation, 1)
            # Control speed
            controls.boost = aerial_intersection_boost < aerial_intersection_jump and my_car.has_wheel_contact == False
            if aerial_intersection_faster < aerial_intersection_jump:
                controls.throttle = 1
            elif aerial_intersection_slower < aerial_intersection_jump:
                controls.throttle = -1
            # Control turn
            if aerial_intersection_right < aerial_intersection_jump:
                controls.steer = 1
            elif aerial_intersection_left < aerial_intersection_jump:
                controls.steer = -1
            # Launch
            if my_car.has_wheel_contact == True and self.jumping < 0 and aerial_intersection_slower > aerial_intersection_jump and aerial_intersection_left > aerial_intersection_jump < aerial_intersection_right:
                self.jumping = 0.2
            if self.jumping < 0 and aerial_intersection_jump < aerial_intersection and get_angle(aerial_front_jump, aerial_front) <= math.pi / 4 and my_car.double_jumped == False and my_car.has_wheel_contact == False:
                self.jump_flip = False
                self.jumping = 2/60
            if get_angle(car_direction, aerial_front) <= math.pi / 4:
                controls.boost = True
            if my_car.has_wheel_contact == True and False:
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
        # Jump to gain power on the hit
        def power_shot():
            # Shorten
            intersectionM = intersect_time_x(packet.game_info.seconds_elapsed, ball_prediction, car_location, clamp(car_velocity.length(), 1410, 2300), max_jump_height(-packet.game_info.world_gravity_z, False), (self.ball_size_setting + 41.095), mid_location, self.dropshot, True, my_car.boost, self.boost_strength_setting, packet)
            intersectionN = nearest_intersection(packet.game_info.seconds_elapsed, ball_prediction, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), (self.ball_size_setting + 41.095), mid_location, self.dropshot, True, packet)
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location * sign((ball_location + send_location).length() - (car_location + send_location).length())) * (self.ball_size_setting + 41.095) * sign((ball_location + send_location).length() - (car_location + send_location).length())
            disparity = (bp - surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, False), self.dropshot), self.dropshot))
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
            controls.boost = (abs(steer_toward_target(my_car, tl)) <= 0.1 or (car_location - tl).length() >= 225000 / 99 * math.sin(get_angle(car_direction, tl - car_location) / 2) and get_angle(car_direction, tl - car_location) < math.pi / 2) and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and (surface_pos(car_location, self.dropshot) - surface_pos(Vec3(predict_ball(intersectionM).physics.location), self.dropshot)).length() * safe_div(intersectionM) >= 1410
            # Jumping
            jump_hold = clamp(intersection - 2 / 60, 2/60, 0.2)
            if (tl - bp).length() <= 100:
                jump_hold = 2 / 60
            # First jump
            if intersection > 0 and my_car.has_wheel_contact == True and self.jumping < 0 and (((intersection <= jt or (ball_location - car_location).length() <= 0.4 * (ball_velocity - car_velocity).length() + self.ball_size_setting) and (abs(steer_toward_target(my_car, tl)) <= 0.1 or (car_location + car_velocity * 0.5 - tl).length() <= 127.02)) or (stop_cond and get_angle(car_velocity, ball_velocity) <= math.pi / 2 and (ball_location - car_location).length() <= 0.4 * (ball_velocity - car_velocity).length() + self.ball_size_setting)) and not (nearest_enemy is not None and disparity <= 120 and get_angle(tl - car_location, Vec3(nearest_enemy.physics.location) - tl) <= math.pi / 6 and nearest_enemy.has_wheel_contact == True):
                self.jumping = jump_hold
            # Speed-flip
            if ball_location.x == 0 and ball_location.y == 0 and get_angle(tl - car_location, car_velocity) <= 0.1 and car_velocity.length() >= 800 and car_velocity.length() <= 2200 and controls.boost == True and (tl - car_location).length() * safe_div(car_velocity.length()) > 2 and my_car.boost >= 10 and surface_pos(car_location, self.dropshot).z == 0:
                override = self.speed_flip(packet, pref_sign(car_location.x * sign(0.5 - self.team), random.choice([-1, 1])))
            # Prepare for frame-perfect hit
            if ((car_location + car_velocity / 30) - (ball_location + ball_velocity / 30)).length() <= 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() > 127.02 + self.ball_size_setting and not (disparity <= 120 and get_angle(tl - car_location, Vec3(nearest_enemy.physics.location) - tl) <= math.pi / 6 and nearest_enemy is not None and nearest_enemy.has_wheel_contact == True):
                self.jumping = -1/60
            # The power hit
            elif my_car.has_wheel_contact == False and self.jumping < 0:
                if (car_location - ball_location).length() > 127.02 + self.ball_size_setting and ((car_location + car_velocity / 60) - (ball_location + ball_velocity / 60)).length() <= 127.02 + self.ball_size_setting:
                    override = self.generic_flip(packet, -flip_value(math.cos(get_angle(dir_convert(Vec3(side_direction.x, side_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0))))) * sign(roof_direction.z), -flip_value(math.cos(get_angle(dir_convert(Vec3(car_direction.x, car_direction.y, 0)), dir_convert(Vec3(ball_location.x - car_location.x, ball_location.y - car_location.y, 0))))), 0, 0, 0.8)
                controls.boost = False
                controls.throttle = 0
            if get_angle(tl - car_location, car_velocity) > math.pi / 2 and sign(steer_toward_target(my_car, tl)) != sign(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))):
                controls.steer = fix_reversing(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location)))
            else:
                controls.steer = fix_reversing(steer_toward_target(my_car, tl))
            return tl
        # Pace
        def pace():
            # Shorten
            intersectionM = intersect_time_x(packet.game_info.seconds_elapsed, ball_prediction, car_location, clamp(car_velocity.length(), 1410, 2300), max_jump_height(-packet.game_info.world_gravity_z, False), (self.ball_size_setting + 41.095), mid_location, self.dropshot, True, my_car.boost, self.boost_strength_setting, packet)
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * (self.ball_size_setting + 41.095)
            disparity = (bp - surface_pos(bp, self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, bp, self.dropshot))
            
            if intersection == 0:
                controls.throttle = 1
            else:
                if sign(max_jump_height(-packet.game_info.world_gravity_z, False) - disparity) == 1 or intersection > intersectionM:
                    controls.throttle = sign(math.pi / 2 - get_angle(car_direction, tl - car_location))
                else:
                    controls.throttle = sign(get_angle(car_direction, tl - car_location) - math.pi / 2)
                    
            controls.boost = abs(steer_toward_target(my_car, tl)) <= 0.1 and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and (surface_pos(car_location, self.dropshot) - surface_pos(Vec3(predict_ball(intersectionM).physics.location), self.dropshot)).length() * safe_div(intersectionM) >= 1410
            if car_velocity.length() >= 800 and car_velocity.length() <= 2200 and controls.boost == True and my_car.boost >= 10:
                override = self.speed_flip(packet, pref_sign(car_location.x, random.choice([-1, 1])))
            return tl
        # Jump to reach the ball
        def reach():
            # Shorten
            intersectionM = intersect_time_x(packet.game_info.seconds_elapsed, ball_prediction, car_location, clamp(car_velocity.length(), 1410, 2300), max_jump_height(-packet.game_info.world_gravity_z, True), self.ball_size_setting, mid_location, self.dropshot, True, my_car.boost, self.boost_strength_setting, packet)
            intersectionN = nearest_intersection(packet.game_info.seconds_elapsed, ball_prediction, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.ball_size_setting, mid_location, self.dropshot, True, packet)
            # Target
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * self.ball_size_setting
            disparity = (bp - surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot)).length()
            tl = outside_goal(car_location, wall_transition_path(car_location, surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, True), self.dropshot), self.dropshot))
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
            controls.boost = abs(steer_toward_target(my_car, tl)) <= 0.1 and controls.throttle == 1 and my_car.jumped == False and car_velocity.length() < 2290 and (surface_pos(car_location, self.dropshot) - surface_pos(Vec3(predict_ball(intersectionM).physics.location), self.dropshot)).length() * safe_div(intersectionM) >= 1410
            
            # Jumping
            jump_hold = 0.2 + clamp(ja - 1, 0, 1) * 13 / 60
            if intersection > 0 and my_car.has_wheel_contact == True and self.jumping < 0 and intersection <= jt and abs(steer_toward_target(my_car, tl)) <= 0.1 and (tl - bp).length() >= 100:
                self.jump_flip = False
                self.jumping = jump_hold
            if my_car.has_wheel_contact == False and get_angle(car_velocity, tl - car_location) < math.pi / 2:
                future_pos = car_location + car_velocity * intersection - Vec3(0, 0, 325) * intersection**2
                controls.pitch, controls.yaw = aerial_control(dir_convert(bp - future_pos), car_rotation, 0.8)
                if not my_car.double_jumped:
                    controls.pitch = 0
            if get_angle(tl - car_location, car_velocity) > math.pi / 2 and sign(steer_toward_target(my_car, tl)) != sign(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location))):
                controls.steer = fix_reversing(steer_toward_target(my_car, Vec3(predict_ball(intersectionN).physics.location)))
            else:
                controls.steer = fix_reversing(steer_toward_target(my_car, tl))
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
            # Flips
            if my_car.has_wheel_contact == True and (car_location - tl).length() > car_velocity.length() * 0.2 + (car_velocity.length() + 292) * 1.5:
                if (my_car.boost == 0 or not emergency) and get_angle(tl - car_location, car_velocity) <= 0.1 and car_velocity.length() > 1000 and surface_pos(car_location, self.dropshot).z == 0 and get_angle(car_velocity, car_direction) <= math.pi / 2:
                    override = self.generic_flip(packet, 0, -1, 8/60, 1/60, 0.8)
                elif get_angle(car_velocity, car_direction) > math.pi - 0.2:
                    override = self.reverse_flip(packet, 1)
            # Speed-flip
            if False and car_velocity.length() >= 800 and car_velocity.length() <= 2200 and controls.boost == True and my_car.boost >= 10 and (car_location - tl).length() > car_velocity.length() * 0.2 + (car_velocity.length() + 292) * 1:
                override = self.speed_flip(packet, pref_sign(car_location.x, random.choice([-1, 1])))
            controls.steer = fix_reversing(steer_toward_target(my_car, tl))
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
            controls.steer = fix_reversing(steer_toward_target(my_car, tl))
            return tl
        # Setup shot
        def setup(cl, tp, hp, slowdown):
            k = get_angle(cl - tp, tp - hp)
            tl = surface_pos(tp - (hp - tp) * safe_div((hp - tp).length()) * clamp((tp - cl).length() / 2, 0, (car_velocity - ball_velocity).length()), self.dropshot)
            if surface_pos(car_location, self.dropshot).y == mid_location.y:
                tl = Vec3(car_location.x, car_location.y, 0)
            controls.steer = fix_reversing(steer_toward_target(my_car, tl))
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
            e_carrying = nearest_enemy is not None and (Vec3(nearest_enemy.physics.velocity) - ball_velocity).length() < 100 and (Vec3(nearest_enemy.physics.location) - ball_location).length() <= 500 and get_angle(car_location - ball_location, -send_location - ball_location) > math.pi / 180 * 26.57
            # Fundamental mode
            if get_angle(Vec3(predict_ball(intersection).physics.location) - car_location, send_location - car_location) <= math.pi / 2 and not e_carrying and (sign(car_velocity.y) * sign(send_location.y) >= 0 or nearest_et >= nearest_ft) or cond_hold or abs(car_location.y + send_location.y) <= car_velocity.length() * 0.75:
                if nearest_et <= 1.5 and predict_ball(intersection).physics.location.z > max_jump_height(-packet.game_info.world_gravity_z, False) / 10 * 9:
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
                if nearest_et < nearest_ft:
                    mode += "_E"
            # Prepare the jump time variable
            bp = Vec3(predict_ball(intersection).physics.location)
            bp = bp - dir_to_point(bp, mid_location) * (self.ball_size_setting + ((self.ball_size_setting + 41.095) - self.ball_size_setting) * bool(mode == "Power shot"))
            disparity = (bp - surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, bool(mode == "Reach")), self.dropshot)).length()
            jt, ja = jump_time(disparity, mode == "Reach")
            # Other variables
            cond_hold = abs(sp.x) > (893 - self.ball_size_setting * 2 + abs(sp.y - send_location.y)) and predict_ball(5).physics.location.x * sign(sp.x) <= (893 - self.ball_size_setting * 2 + abs(sp.y - send_location.y))
            # Complimentary mode
            if mode != "Aerial" and ((my_car.has_wheel_contact == False and get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) <= math.pi / 2) or get_angle(car_direction, car_velocity) > math.pi / 8):
                mode_comp = "Recovery"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and nearest_et < nearest_ft and (car_location - ball_location).length() * safe_div((car_velocity - ball_velocity).length()) >= get_angle(car_direction, ball_location - car_location) and intersection > jt + get_angle(car_velocity, ball_location - car_location):
                mode_comp = "Shadow"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and ball_location.x * ball_location.y != 0 and (nearest_et > nearest_ft + 0.2 or (cond_hold)) and (car_location - ball_location).length() * safe_div((car_velocity - ball_velocity).length()) >= get_angle(car_direction, ball_location - car_location) and intersection > jt + get_angle(car_velocity, ball_location - car_location):
                if cond_hold:
                    mode_comp = "Hold off"
                else:
                    mode_comp = "Setup"
            return mode, mode_comp
        # 2v2 (Soccer)
        def doubles():
            mode, mode_comp = "", ""
            return mode, mode_comp
        # 3v3 (Soccer)
        def standard():
            mode, mode_comp = "", ""
            return mode, mode_comp
        # 4v4 (Soccer)
        def chaos():
            mode, mode_comp = "", ""
            return mode, mode_comp
        # 1v1 (Dropshot)
        def duel_dropshot():
            mode, mode_comp = "", ""
            if aerial_intersection > 0 and ((Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos(Vec3(predict_ball(aerial_intersection).physics.location), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, True) or (nearest_enemy is None or nearest_enemy.has_wheel_contact == False and nearest_friendly == my_car and (Vec3(predict_ball(aerial_intersection).physics.location) - surface_pos(Vec3(predict_ball(aerial_intersection).physics.location), self.dropshot)).length() > max_jump_height(-packet.game_info.world_gravity_z, False) and (nearest_enemy is None or nearest_et > aerial_intersection + get_angle(car_direction, aerial_front) / 6 and False))):
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
            disparity = (bp - surface_pos_two(bp, car_location, max_jump_height(-packet.game_info.world_gravity_z, bool(mode == "Reach")), self.dropshot)).length()
            jt, ja = jump_time(disparity, mode == "Reach")
            # Complimentary mode
            if mode != "Aerial" and ((my_car.has_wheel_contact == False and get_angle(car_velocity, surface_pos(car_location, self.dropshot) - car_location) <= math.pi / 2) or get_angle(car_direction, car_velocity) > math.pi / 8):
                mode_comp = "Recovery"
            elif mode not in ["Aerial", "Retreat", "Retreat_E"] and nearest_et > nearest_ft + 0.2 and intersection > jt + get_angle(car_velocity, ball_location - car_location) and sign(ball_location.y + ball_velocity.y * nearest_ft) == -sign(send_location.y) and packet.game_ball.latest_touch.team == self.team:
                mode_comp = "Setup"
            '''
            return mode, mode_comp
        # 2v2 (Dropshot)
        def doubles_dropshot():
            mode, mode_comp = "", ""
            return mode, mode_comp
        # 3v3 (Dropshot)
        def standard_dropshot():
            mode, mode_comp = "", ""
            return mode, mode_comp
        # 4v4 (Dropshot)
        def chaos_dropshot():
            mode, mode_comp = "", ""
            return mode, mode_comp
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
        send_location, mid_location = get_send()
        number_friendly, number_enemy = player_count()
        nearest_friendly, nearest_ft = read_players(400, True)
        role_in_team = distance_order()
        nearest_enemy, nearest_et = read_players(400, False)
        angle_disparity = get_angle(Vec3(-800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0))
        angle_comparison = get_angle(Vec3(-800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(car_direction.x, car_direction.y, 0)) + get_angle(Vec3(800, -send_location.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(car_direction.x, car_direction.y, 0))
        mode = ""
        mode_comp = ""
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

        controls = SimpleControllerState()
        predict_pos = Vec3(predict_ball(aerial_intersection).physics.location)
        # Modes and Team size
        if False:
            mode, mode_comp = behaviour_x()
        elif self.dropshot == True:
            if number_friendly >= 1:
                mode, mode_comp = duel_dropshot()
            elif number_friendly == 2:
                mode, mode_comp = doubles_dropshot()
            elif number_friendly == 3:
                mode, mode_comp = standard_dropshot()
            elif number_friendly >= 4:
                mode, mode_comp = chaos_dropshot()
        else:
            if number_friendly >= 1:
                mode, mode_comp = duel()
            elif number_friendly == 2:
                mode, mode_comp = doubles()
            elif number_friendly == 3:
                mode, mode_comp = standard()
            elif number_friendly >= 4:
                mode, mode_comp = chaos()
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
        if mode_comp == "Recovery":
            recovery()
        elif mode_comp == "Setup":
            target_location = setup(car_location, target_location, mid_location, False)
        elif mode_comp == "Shadow":
            target_location = setup(car_location, target_location, (ball_location + ball_velocity * nearest_et) * 2 + mid_location, False)
        elif mode_comp == "Refuel":
            target_location = refuel()
        elif mode_comp == "Hold off":
            target_location = setup(car_location, target_location, mid_location, True)
        elif mode_comp == "Swipe":
            swipe()
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
        if self.no_hold_off_time <= 1 / 60 and mode in ["Power shot", "Reach"]:
            controls.boost = False
        self.no_hold_off_time += 1/60

        self.renderer.draw_line_3d(car_location, surface_pos(car_location, self.dropshot), self.renderer.white())
        self.renderer.draw_string_3d(car_location, 1, 1, mode + " (" + mode_comp + ")", self.renderer.white())
        for i in range(140):
            self.renderer.draw_string_3d(get_pos(i), 1, 1, str(i), self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        self.renderer.draw_rect_3d(send_location, 8, 8, True, self.renderer.green(), centered=True)
        # The bot's personality in chat
        if my_car.is_demolished == True:
            self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Compliments_Thanks)
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
