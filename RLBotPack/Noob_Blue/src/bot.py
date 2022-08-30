from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import *
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3
import math

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def initialize_agent(self):
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        settings = self.get_match_settings()
        self.jump_time = 0
        self.map = settings.GameMap()
        if self.map == 35:
            self.map_size = [3581, 2966.7]
        elif self.map == 31:
            self.map_size = [5139.7, 4184.5]
        elif self.map == 37:
            self.map_size = [6912, 4096]
        else:
            self.map_size = [5120, 4096]

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        self.boost_pad_tracker.update_boost_status(packet)

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        # Update the send location to hit ball past others
        def hit_past(tl):
            angles = [-math.pi / 3, math.pi / 3]
            for car in packet.game_cars:
                test_pos = Vec3(car.physics.location) + Vec3(car.physics.velocity) * friendly_time
                test_pos = Vec3(test_pos.x, test_pos.y, 0)
                gap = Vec3(tl.x, tl.y, 0) - Vec3(car_location.x, car_location.y, 0)
                gapL = Vec3(gap.y, -gap.x, 0)
                gapR = Vec3(-gap.y, gap.x, 0)
                a1 = get_angle(Vec3(tl.x, tl.y, 0) - Vec3(car_location.x, car_location.y, 0), Vec3(test_pos.x, test_pos.y, 0) - Vec3(tl.x, tl.y, 0))
                a1 = a1 * sign((gapL + car_location - test_pos).length() - (gapR + car_location - test_pos).length())
                if -math.pi / 3 < a1 < math.pi / 3:
                    for i in range(len(angles) - 1):
                        if angles[i] < a1 < angles[i + 1]:
                            angles.insert(a1, i + 1)
            if len(angles) > 2:
                furthest_gap = 0
                best_gap = 0
                for i in range(len(angles) - 1):
                    if angles[i + 1] - angles[i] > furthest_gap:
                        best_gap = i
                        furthest_gap = angles[i + 1] - angles[i]
                new_angle = (angles[best_gap + 1] + angles[best_gap]) / 2
                return (angles[best_gap + 1] + angles[best_gap]) / 2
        # Get the distance from the nearest surface (walls, floor, roof, etc.)
        def distance_from_surface(pos):
            min_dist = math.inf
            nearest_surface = pos
            if min_dist > pos.z:
                min_dist = pos.z
                nearest_surface = Vec3(pos.x, pos.y, 0)
            if min_dist > self.map_size[1] - abs(pos.x):
                min_dist = self.map_size[1] - abs(pos.x)
                nearest_surface = Vec3(sign(pos.x) * self.map_size[1], pos.y, pos.z)
            if min_dist > self.map_size[0] - abs(pos.y):
                min_dist = self.map_size[0] - abs(pos.y)
                nearest_surface = Vec3(pos.x, sign(pos.y) * self.map_size[0], pos.z)
            return nearest_surface
        # Get the rate in which the object is moving away from the nearest surface
        def velocity_from_surface(pos, vel):
            val = pos - distance_from_surface(pos)
            if val.x != 0:
                return vel.x * sign(val.x)
            elif val.y != 0:
                return vel.y * sign(val.y)
            elif val.z != 0:
                return vel.z * sign(val.z)
            else:
                return 0
        # Direction of position (position(Vec3))
        def dir_convert(pos):
            return pos * safe_div(pos.length())
        # Get the order within the team
        def distance_order(teams):
            nearest = 1
            overall_nearest = 1
            last = 0
            ref = (car_location - ball_location).length() / (car_velocity.length() + 2300) + math.asin((car_velocity * safe_div(car_velocity.length()) - ball_location * safe_div(ball_location.length())).length() / 2) * 3 / math.pi * 0
            for i in range(len(packet.game_cars)):
                if (packet.game_cars[i].team != (-teams * packet.game_cars[self.index].team + (1 + teams) / 2) or teams == False) and packet.game_cars[i].physics.location.z > 0:
                    time_taken = (Vec3(packet.game_cars[i].physics.location) - ball_location).length() / (Vec3(packet.game_cars[i].physics.velocity).length() + 2300) + (velocity_from_surface(Vec3(0, 0, Vec3(packet.game_cars[i].physics.location).z), Vec3(packet.game_cars[i].physics.velocity)) / 650 + math.sqrt(velocity_from_surface(Vec3(0, 0, Vec3(packet.game_cars[i].physics.location).z), Vec3(packet.game_cars[i].physics.velocity))**2 / 650**2 + Vec3(packet.game_cars[i].physics.location).z / 325) * sign(Vec3(packet.game_cars[i].physics.velocity).y)) * bool()
                    # When the car is further front than the POV
                    if ref > time_taken:
                        if ((Vec3(packet.game_cars[i].physics.location) + send_location).length() <= (ball_location + send_location).length() or (car_location + send_location).length() > (ball_location + send_location).length()):
                            nearest += 1
                        overall_nearest += 1
                    last += 1
            # Keep the full-time goal keeper
            if overall_nearest == last:
                nearest = overall_nearest
            # Prevent the division by 0 error
            return last, nearest
        # Find the best boost pads to use to refuel as fast as possible
        def find_best_boost_pads():
            best_pad = None
            best_score = math.inf
            for i in range(len(self.get_field_info().boost_pads)):
                pad = self.get_field_info().boost_pads[i]
                if packet.game_boosts[i].is_active == True or packet.game_boosts[i].timer <= (Vec3(pad.location) - car_location).length() / 2300:
                    score = (Vec3(pad.location) - car_location).length() * safe_div(car_velocity.length()) + math.sin(((Vec3(pad.location) - car_location) / (Vec3(pad.location) - car_location).length() - car_velocity * safe_div(car_velocity.length())).length() / 2) * 3 / math.pi
                    if pad.is_full_boost:
                        score *= safe_div((50 - my_car.boost / 2) / 6)
                    if score < best_score:
                        best_score = score
                        best_pad = pad
            return best_pad
        # Get the yaw based on position
        def get_yaw(x, y):
            a = math.acos(x / Vec3(x, y, 0).length())
            if abs(a) < math.pi:
                return a * sign(y)
            else:
                return math.pi
        # Get the angle between two places
        def get_angle(p1, p2):
            d = (p1 * safe_div(p1.length()) - p2 * safe_div(p2.length())).length()
            angle = 2 * math.asin(d / 2)
            return angle
        # Determine when the car would intersect the ball assuming a speed
        def intersect_time(surface):
            t1 = 5
            t2 = 5
            best_spd = math.inf
            slowest = math.inf
            if surface == False:
                for i in range(1, 101):
                    time_location = Vec3(predict_ball(i / 20).physics.location)
                    time_location = time_location - (send_location - time_location) * safe_div((send_location - time_location).length()) * ball_offset
                    if (time_location - car_location).length() * 20 / i <= car_velocity.length() and t1 == 5:
                        t1 = i / 20
                    if (time_location - car_location).length() * 20 / i <= slowest:
                        slowest = (time_location - car_location).length() * 20 / i
                        t2 = i / 20
            else:
                for i in range(1, 101):
                    time_location = Vec3(predict_ball(i / 20).physics.location)
                    time_location = time_location - (send_location - time_location) * safe_div((send_location - time_location).length()) * ball_offset
                    if (distance_from_surface(time_location) - distance_from_surface(car_location)).length() * 20 / i <= car_velocity.length() and t1 == 5:
                        t1 = i / 20
                    if (distance_from_surface(time_location) - distance_from_surface(car_location)).length() * 20 / i <= slowest:
                        slowest = (distance_from_surface(time_location) - distance_from_surface(car_location)).length() * 20 / i
                        t2 = i / 20
                    
            return t1, t2
        # Determine when the car would intersect the ball in the air
        def intersect_aerial(pos, vel):
            for i in range(1, 101):
                t = i / 20
                time_location = Vec3(predict_ball(t).physics.location)
                time_location = time_location - (send_location - time_location) * safe_div((send_location - time_location).length()) * (92.75)
                car_pos = car_location + car_velocity * t - Vec3(0, 0, 325 * t**2)
                r = 5950 / 12 * t**2
                if (time_location - car_pos).length() <= r:
                    return t, (time_location - car_pos) * safe_div((time_location - car_pos).length())
            return 0, car_direction
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
        # Determine when the car should jump
        def jump_ready(h, double):
            if h <= 74.6:
                return -292 / 810 + math.sqrt(h / 405 + (292 / 810)**2)
            elif h <= -29.2 + 584 * 292 / 325 - 325 * 292**2 / 325**2 and not double:
                return 292 / 325 - math.sqrt(-h / 325 - 29.2 / 325 + (292 / 325)**2)
            elif h <= 876 * 438 / 325 - 325 * (438 / 325)**2 - 584 / 6 and double:
                return 438 / 325 - math.sqrt(-h / 325 + (438 / 325)**2 - 584 / 1950)
            else:
                return 0
        # Get the nearest player to the ball
        def nearest_player(teams, speed_offset):
            nearest = None
            best_time = math.inf
            last = True
            for i in range(len(packet.game_cars)):
                if (packet.game_cars[i].team != (-teams * packet.game_cars[self.index].team + (1 + teams) / 2) or teams == False) and Vec3(packet.game_cars[i].physics.location) != Vec3(0, 0, 0):
                    time_taken = (Vec3(packet.game_cars[i].physics.location) - ball_location).length() / (Vec3(packet.game_cars[i].physics.velocity).length() + speed_offset) + math.sin((Vec3(packet.game_cars[i].physics.velocity) * safe_div(Vec3(packet.game_cars[i].physics.velocity).length()) - ball_location * safe_div(ball_location.length())).length() / 2) * 3 / math.pi
                    if time_taken < best_time:
                        best_time = time_taken
                        nearest = packet.game_cars[i]
            return nearest, best_time
        # Get the list of moments when the ball should be hit
        def opportunities():
            li = []
            prev_pos = ball_location
            for i in range(1, 101):
                time_location = predict_ball(i / 20)
                if time_location.z <= 300:
                    li.append([i / 20, (time_location - car_location).length() * 20 / i])
                prev_pos = time_location
            return li
        # ???
        def plane_dist(pos, dist):
            if Vec3(pos.x, pos.y, 0).length() <= dist:
                return True
            elif Vec3(pos.x, 0, pos.z).length() <= dist:
                return True
            elif Vec3(0, pos.y, pos.z).length() <= dist:
                return True
            else:
                return False
        # Get the ball's position and velocity at a specific time
        def predict_ball(t):
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + t)
            if ball_in_future is not None:
                return ball_in_future
            else:
                return packet.game_ball
        # Divide numbers without division by 0
        def safe_div(x):
            if x == 0:
                return math.inf
            else:
                return 1 / x
        # Return the direction of the value from 0
        def sign(x):
            if x < 0:
                return -1
            elif x > 0:
                return 1
            else:
                return 0
        # Return a value with limitations
        def clamp(x, m, M):
            if x < m:
                return m
            elif x > M:
                return M
            else:
                return x
        # Move the target location to straighten the ascent up walls
        def move_target_for_walls(pos1, pos2):
            up1 = distance_from_surface(pos1)
            up2 = distance_from_surface(pos2)
            new_pos = pos2
            if up1.z == 0 and up2.z > 0:
                new_pos = Vec3(new_pos, 0, new_pos) + (up2 - pos2) * safe_div((up2 - pos2).length()) * up2.z
            if up1.z > 0 and up2.z == 0 and pos1.z >= 30:
                if abs(up1.x) == self.map_size[1]:
                    new_pos = Vec3(up1.x, up2.y, -abs(up2.x - up1.x))
                elif abs(up1.y) == self.map_size[0]:
                    new_pos = Vec3(up2.x, up1.y, -abs(up2.y - up1.y))
            return new_pos
        
        # Actions
        # Use flip jumps to attack the ball
        def jump_attack():
            dir_y = 0
            dir_x = 0
            if ((car_location + car_velocity / 5) - (ball_location + ball_velocity / 5)).length() <= 175:
                if (car_location + Vec3(car_velocity.y, -car_velocity.x, 0) * safe_div(car_velocity.length()) - ball_location).length() < (car_location - ball_location).length():
                    dir_x = -1
                if (car_location + Vec3(-car_velocity.y, car_velocity.x, 0) * safe_div(car_velocity.length()) - ball_location).length() < (car_location - ball_location).length():
                    dir_x = 1
                if (car_location + car_velocity / 5 - ball_location - ball_velocity / 5).length() <= (car_location - ball_location).length() - 50:
                    dir_y = -1
                dir_x *= sign(math.pi / 2 - get_angle(car_direction, car_velocity))
                dir_y *= sign(math.pi / 2 - get_angle(car_direction, car_velocity))
                override = self.flip(packet, dir_x, dir_y, not my_car.jumped)
        # Jump over cars to prevent collision
        def avoid_bump():
            if my_car.has_wheel_contact == True and self.jump_time < 0:
                for i in range(len(packet.game_cars)):
                    if (ball_location - car_location).length() > (Vec3(packet.game_cars[i].physics.location) - car_location).length():
                        if i != self.index and packet.game_cars[i].physics.location.z > 0:
                            vel = car_velocity
                            vel2 = Vec3(packet.game_cars[i].physics.velocity)
                            pos = car_location + vel * 0.2
                            pos2 = Vec3(packet.game_cars[i].physics.location) + vel2 * 0.2
                            dist = (pos - pos2).length()
                            on_course = False
                            if dist > 118.01:
                                if get_angle(pos2 - pos, vel) <= math.tan(math.sqrt(118.01**2 / (dist**2 - 118.01**2))):
                                    on_course = True
                            else:
                                on_course = True
                            if on_course == True and dist <= 118.01 + (vel - vel2).length() / 2 and (vel.length() <= vel2.length() or packet.game_cars[i].team != self.team):
                                self.jump_time = 1 / 60
        
        # Modes
        def attack():
            # Target
            target_ball = predict_ball(earliest_intersection)
            target_location = Vec3(target_ball.physics.location)
            target_location = target_location + (target_location - send_location) / (target_location - send_location).length() * ball_offset
            # Smoother wall transitions
            target_location = move_target_for_walls(car_location, target_location)
            if 0 < aerial_time < my_car.boost / 100 * 3 and (steer_toward_target(my_car, target_location) <= 0.1 or my_car.has_wheel_contact == False) and ((Vec3(predict_ball(aerial_time).physics.location) - distance_from_surface(Vec3(predict_ball(aerial_time).physics.location))).length() > 500 or car_velocity.length() > 1410):
                # Aerial
                controls.pitch, controls.yaw = aerial_control(aerial_dir, car_rotation, 1)
                controls.boost = get_angle(car_direction, aerial_dir) <= math.pi / 4
                if self.jump_time < 0 and aerial_time_j < aerial_time:
                    self.jump_time = 0.2
                    controls.pitch = 0
                    controls.yaw = 0
                elif self.jump_time > 0 and aerial_time_j > aerial_time:
                    self.jump_time = 0
            else:
                # No aerial
                jumping = jump_ready((target_location - distance_from_surface(target_location)).length(), double_jumping)
                # Manage speed
                if velocity_from_surface(Vec3(target_ball.physics.location), Vec3(target_ball.physics.velocity)) >= 0 or jump_ready((Vec3(target_ball.physics.location) - distance_from_surface(Vec3(target_ball.physics.location))).length(), double_jumping) > 0 or target_location.y * sign(send_location.y) <= -self.map_size[0]:
                    controls.throttle = 1
                else:
                    controls.throttle = -1
                # Boost
                controls.boost = abs(steer_toward_target(my_car, target_location)) <= 0.1 and car_velocity.length() < 2300 and ((Vec3(target_ball.physics.location) - distance_from_surface(Vec3(target_ball.physics.location))).length() <= 300 or velocity_from_surface(Vec3(target_ball.physics.location), Vec3(target_ball.physics.velocity)) >= 0) and car_index == 1
                # Jump
                h = (Vec3(target_ball.physics.location) - distance_from_surface(Vec3(target_ball.physics.location))).length()
                if jump_ready((Vec3(target_ball.physics.location) - distance_from_surface(Vec3(target_ball.physics.location))).length(), double_jumping) >= earliest_intersection and steer_toward_target(my_car, target_location) < 0.1 and my_car.has_wheel_contact == True:
                    controls.pitch = 0
                    controls.yaw = 0
                    controls.roll = 0
                    self.jump_time = 0.2
                    controls.boost = False
                else:
                    jump_attack()
                # Double jump
                if double_jumping == True and self.jump_time < 0 and my_car.jumped == True:
                    controls.pitch = 0
                    controls.yaw = 0
                    controls.roll = 0
                    self.jump_time = 1/60
                if my_car.has_wheel_contact == False:
                    controls.boost = False
                # Catch the ball when in the air
                if abs(target_location.z - car_location.z) <= 92.75 * 0.75 and get_angle(target_location - car_location, car_velocity) >= math.atan(200 * safe_div(car_velocity.length())) and my_car.jumped == True and my_car.double_jumped == False and False:
                    controls.yaw = sign((target_location - car_location - Vec3(car_velocity.y, -car_velocity.x, car_velocity.z)).length() - (target_location - car_location - Vec3(-car_velocity.y, car_velocity.x, car_velocity.z)).length())
                    self.jump_time = 1/60
                # Draw
                self.renderer.draw_line_3d(car_location, target_location, self.renderer.red())
                self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.red(), centered=True)
            return target_location
            
        def standby():
            # Friendly/enemey
            if enemy_time >= friendly_time + 0.2:
                nearest_ref = nearest_friendly
                md = "friendly"
            else:
                nearest_ref = nearest_enemy
                md = "enemy"
            # Target
            if md == "enemy" or True:
                target_location = ball_location - (Vec3(nearest_ref.physics.location) - ball_location) / (Vec3(nearest_ref.physics.location) - ball_location).length() * (2500 + Vec3(nearest_ref.physics.velocity).length() * 5 / 2.3)
                target_location = Vec3(target_location.x, ball_location.y + (target_location.y - ball_location.y) * sign(target_location.y - ball_location.y) * -sign(send_location.y), target_location.z)
            else:
                target_location = ball_location - (Vec3(nearest_ref.physics.location) - ball_location) / (Vec3(nearest_ref.physics.location) - ball_location).length() * (2500 + Vec3(nearest_ref.physics.velocity).length() * 5 / 2.3)
                target_location = target_location + (target_location - send_location) / (target_location - send_location).length() * 927.5
            # Walls
            if (distance_from_surface(target_location) - target_location).length() <= 300:
                target_location = distance_from_surface(target_location)
                target_location = move_target_for_walls(car_location, target_location)
            else:
                target_location = Vec3(target_location.x, target_location.y, 0)
            # Draw
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.green())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.green(), centered=True)
            # Manage speed
            controls.boost = False
            controls.throttle = clamp((target_location - car_location).length() / 1000, -1, 1)
            return target_location
            
        def refuel():
            # Target
            best_pad = find_best_boost_pads()
            target_location = Vec3(best_pad.location)
            # Draw
            self.renderer.draw_line_3d(car_location, target_location, self.renderer.green())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.green(), centered=True)
            # Speed
            controls.throttle = 1
            if best_pad.is_full_boost == True and my_car.has_wheel_contact == True:
                controls.boost = True
            else:
                controls.boost = False
            return target_location
            
        def goalie():
            target_location = car_location
            # Roll back onto the wheels
            if abs(car_rotation.roll) >= math.pi * 3 / 4:
                override = self.jump_once(packet)
            # Prepare for a save
            if sign(car_location.y) == -sign(send_location.y) and abs(car_location.y) >= abs(send_location.y):
                target_location = car_location - Vec3(0, send_location.y, 0)
                if car_velocity.length() >= 850 or get_angle(car_velocity, car_direction) > math.pi / 2:
                    controls.throttle = -sign(math.pi / 2 - get_angle(car_velocity, car_direction))
                else:
                    if Vec3(car_velocity.x, car_velocity.y, 0).length() >= 250 and get_angle(send_location, car_direction) > math.pi / 2:
                        override = self.reverse_flip(packet)
                    else:
                        controls.pitch = 0
                        controls.roll = 0
                        if (not math.pi * 0.4 <= abs(car_rotation.yaw) <= math.pi * 0.6 or sign(car_rotation.yaw) == -sign(send_location.y)) and abs(car_velocity.z) <= 1:
                            override = self.jump_once(packet)
                        controls.yaw = clamp(steer_toward_target(my_car, send_location) - my_car.physics.angular_velocity.z, -1, 1)
                    controls.throttle = 0
            # Drive into the goal unless it's already done so
            else:
                target_location = defend()
            return target_location
            
        def defend():
            if not in_goal and False:
                target_ball = predict_ball(earliest_intersection)
                target_location = Vec3(target_ball.physics.location)
                nearest_surface = (target_location - car_location) / (target_location - car_location).length() * 140
                nearest_surface_r = Vec3(-nearest_surface.y, nearest_surface.x, nearest_surface.z)
                nearest_surface_l = Vec3(nearest_surface.y, -nearest_surface.x, nearest_surface.z)
                if False:
                    side = -sign((nearest_surface_l - send_location).length() - (nearest_surface_r - send_location).length())
                else:
                    side = -sign(((nearest_surface_l - ball_location) - ball_velocity).length() - ((nearest_surface_r - ball_location) - ball_velocity).length())
                nearest_surface = Vec3(-nearest_surface.y * side, nearest_surface.x * side, nearest_surface.z)
                if abs(target_location.x + nearest_surface.x) >= self.map_size[1] or get_angle(car_location - send_location, car_location - target_location) > math.pi / 3 * 2 or ball_location.z > 130:
                    target_location = -send_location
                else:
                    target_location = target_location + nearest_surface / 140 * car_velocity.length()
                controls.boost = enemy_time < 1 and abs(steer_toward_target(my_car, target_location)) <= 0.1
                # Jump
                h = (Vec3(target_ball.physics.location) - distance_from_surface(Vec3(target_ball.physics.location))).length()
                if jump_ready(h, double_jumping) >= earliest_intersection and steer_toward_target(my_car, target_location) < 1:
                    controls.pitch = 0
                    controls.yaw = 0
                    controls.roll = 0
                    self.jump_time = 0.2
                    controls.boost = False
                else:
                    jump_attack()
                # Draw
                self.renderer.draw_line_3d(car_location, ball_location + nearest_surface, self.renderer.cyan())
                self.renderer.draw_rect_3d(ball_location + nearest_surface, 8, 8, True, self.renderer.cyan(), centered=True)
                controls.throttle = 1
            else:
                target_location = -send_location
                if my_car.has_wheel_contact == True:
                    if (target_location - car_location).length() > car_velocity.length() * 1.3 + 292 * 1.2 and car_velocity.length() > 1000:
                        if get_angle(car_direction, car_velocity) > math.pi / 2:
                            override = self.reverse_flip(packet)
                        elif car_velocity.length() < 2290 and get_angle(target_location - car_location, car_direction) <= 0.1:
                            override = self.flip(packet, 0, -1, 0.1)
                controls.throttle = sign((math.pi / 2 - get_angle(-send_location - car_location, car_direction)) - car_velocity.length() / 2300 * sign(math.pi / 2 - get_angle(-send_location - car_location, car_direction)))
            return target_location
            
        def recovery():
            tx = (self.map_size[1] - car_location.x * sign(car_velocity.x)) * safe_div(car_velocity.x)
            ty = (self.map_size[0] - car_location.y * sign(car_velocity.y)) * safe_div(car_velocity.y)
            tt = 0
            if car_location.z / 325 - (car_velocity.z / 650)**2 >= 0:
                tz = car_velocity.z / 650 + math.sqrt(car_location.z / 325 - (car_velocity.z / 650)**2)
            else:
                tz = car_velocity.z / 650 - math.sqrt(car_location.z / 325 + (car_velocity.z / 650)**2)
            if tx >= tz <= ty:
                controls.roll = clamp(-car_rotation.roll, -1, 1)
                controls.pitch = clamp(-car_rotation.pitch, -1, 1)
                tt = tz
            elif tx >= ty <= tz:
                point = (math.pi / 2 + sign(abs(car_rotation.yaw) - math.pi / 2) * math.pi / 2) * sign(car_rotation.yaw)
                controls.roll = clamp(math.pi / 2 * sign(car_velocity.y) * sign(abs(car_rotation.yaw) - math.pi / 2) - car_rotation.roll, -1, 1)
                controls.pitch = clamp(point - car_rotation.yaw, -1, 1)
                tt = ty
            draw_point = Vec3(car_location.x + car_velocity.x * tt, car_location.y + car_velocity.y * tt, car_location.z + car_velocity.z * tt - 325 * tt**2)
            self.renderer.draw_line_3d(car_location, draw_point, self.renderer.pink())
            self.renderer.draw_rect_3d(draw_point, 8, 8, True, self.renderer.pink(), centered=True)
        
        # Variables
        
        
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        car_rotation = my_car.physics.rotation
        car_direction = Vec3(math.cos(car_rotation.yaw) * math.cos(car_rotation.pitch), math.sin(car_rotation.yaw) * math.cos(car_rotation.pitch), math.sin(car_rotation.pitch))
        roof_direction = Vec3(-math.cos(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(car_rotation.roll) + math.sin(car_rotation.yaw) * math.sin(car_rotation.roll), -math.sin(car_rotation.yaw) * math.sin(car_rotation.pitch) * math.cos(car_rotation.roll) - math.cos(car_rotation.yaw) * math.sin(car_rotation.roll), math.cos(car_rotation.roll) * math.cos(car_rotation.pitch))
        ball_prediction = self.get_ball_prediction_struct()
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        send_location = Vec3(0, sign(0.5 - self.team) * self.map_size[0], 0)
        team_size, car_index = distance_order(1)
        nearest_enemy, enemy_time = nearest_player(0, 460)
        nearest_friendly, friendly_time = nearest_player(0, 460)
        double_jumping = enemy_time <= 1.5
        ball_offset = 92.75 + 42.1 * bool(not double_jumping)
        aerial_time, aerial_dir = intersect_aerial(car_location, car_velocity)
        next_jump_offset = 1460 / (60 - bool(self.jump_time <= 0) * 55)
        aerial_time_j, aerial_dir_j = intersect_aerial(car_location, car_velocity + roof_direction * next_jump_offset)
        earliest_intersection, easiest_intersection = intersect_time(True)
        emergency = predict_future_goal(ball_prediction)
        in_goal = (ball_location + send_location).length() > (car_location + send_location).length()
        target_location = car_location
        mode = ""
        override = None

        # Controls
        controls = SimpleControllerState()
        
        # Half-flip to quickly turn
        if car_velocity.length() <= 500 and get_angle(car_velocity, target_location - car_location) >= math.pi / 3 * 2:
            override = self.reverse_flip(packet)
        
        # Assign role in the team
        if abs(send_location.y + Vec3(predict_ball(2).physics.location).y) <= 1000 or abs(send_location.y + ball_location.y) <= 1000:
            if in_goal:
                mode = "Attack"
            else:
                mode = "Defense"
        else:
            if car_index == 1:
                if in_goal:
                    mode = "Attack"
                else:
                    mode = "Defense"
            elif car_index < team_size:
                if my_car.boost == 100 and car_index == 2:
                    mode = "Standby"
                else:
                    mode = "Refuel"
            else:
                mode = "Goalie"
        # Recovery
        if velocity_from_surface(car_location, car_velocity) < 0 and mode != "Goalie":
            recovery()
        # Demolition
        if mode == "Demo":
            target_location = demo()
        # Attack the ball
        if mode == "Attack":
            avoid_bump()
            target_location = attack()
            controls.use_item = True
        # Stand by for hit
        if mode == "Standby":
            avoid_bump()
            target_location = standby()
        # Collect boost
        if mode == "Refuel":
            avoid_bump()
            target_location = refuel()
        # Retreat
        if mode == "Defense":
            avoid_bump()
            target_location = defend()
        # Goalie
        if mode == "Goalie":
            avoid_bump()
            target_location = goalie()
            
        if get_angle(car_direction, car_velocity) <= math.pi / 2:
            controls.steer = steer_toward_target(my_car, target_location)
        else:
            controls.steer = steer_toward_target(my_car, target_location) * clamp(get_angle(car_direction, -car_velocity) * 5, 0, 1)
        
        controls.jump = self.jump_time > 0
        self.jump_time = clamp(self.jump_time - 1 / 60, -1 / 60, math.inf)
        
        # Draw
        if False:
            self.renderer.draw_string_2d(800, 200, 1, 1, "X: " + str(packet.game_cars[1 - self.index].physics.location.x), self.renderer.white())
            self.renderer.draw_string_2d(800, 220, 1, 1, "Y: " + str(packet.game_cars[1 - self.index].physics.location.y), self.renderer.white())
            self.renderer.draw_string_2d(1400, 200, 1, 1, "Map: " + str(self.map), self.renderer.white())
        self.renderer.draw_string_2d(50, 680 + car_index * 20 * (0.5 - self.team) * 2, 1, 1, "Noob Bot " + str(car_index) + ": " + str(mode) + ", double jump: " + str(double_jumping), self.renderer.white())
        self.renderer.draw_line_3d(target_location, distance_from_surface(target_location), self.renderer.yellow())
        self.renderer.draw_line_3d(car_location, car_location + aerial_dir * 1000, self.renderer.red())
        
        if override:
            return override
        else:
            return controls

    def flip(self, packet, dir_x, dir_y, first_jump):
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=first_jump)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, yaw=dir_x, pitch=dir_y)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        return self.active_sequence.tick(packet)

    def jump_once(self, packet):
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False))
        ])

        return self.active_sequence.tick(packet)

    def reverse_flip(self, packet):
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=1)),
            ControlStep(duration=0.25, controls=SimpleControllerState(jump=False, pitch=-1)),
            ControlStep(duration=0.3, controls=SimpleControllerState(roll=1, pitch=-1)),
            ControlStep(duration=0.05, controls=SimpleControllerState()),
        ])

        return self.active_sequence.tick(packet)

    def correct_direction(self, packet, dir):
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True, throttle = dir)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False, throttle = dir)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, throttle = dir, pitch=1)),
            ControlStep(duration=0.25, controls=SimpleControllerState(jump=False, throttle = dir, pitch=-1)),
            ControlStep(duration=0.3, controls=SimpleControllerState(roll=1, throttle = -dir, pitch=-1)),
            ControlStep(duration=0.05, controls=SimpleControllerState(throttle = -dir)),
        ])

        return self.active_sequence.tick(packet)
