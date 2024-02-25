from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

import math, random, time

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.jump_time = 0
        self.jump_dir = Vec3(0, 0, 0)
        self.flip_time = 0
        self.prev_rot = [0, 0, 0]
        self.schedule_vel = Vec3(-2000 + random.random() * 4000, -2000 + random.random() * 4000, 0)

    def initialize_agent(self):
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.boost_pad_tracker.update_boost_status(packet)

        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls
        def get_players(packet):
            li = [[], []]
            index = 0
            for i in range(len(packet.game_cars)):
                car = packet.game_cars[i]
                if car.name != "":
                    li[car.team].append(i)
                    if i == self.index:
                        index = len(li[car.team]) - 1
            return li, index
        def brake_distance(v1, v2, s):
            d1 = v1**2 / (s * 2)
            d2 = v2**2 / (s * 2)
            return d1 - d2
        def car_dir(pitch, yaw):
            return Vec3(math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch))
        def sign(x):
            if x < 0:
                return -1
            elif x > 0:
                return 1
            else:
                return 0
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
        def clamp(x, m, M):
            if x > M:
                return M
            elif x < m:
                return m
            else:
                return x
        def safe_div(x):
            if x == 0:
                return math.inf
            else:
                return 1 / x
        def predict_ball(t):
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + t)
            if ball_in_future is not None:
                return ball_in_future
            else:
                return packet.game_ball
        def surface_pos(p):
            best = p.z
            np = Vec3(p.x, p.y, 0)
            if 0 <= 4096 - abs(p.x) < best:
                np = Vec3(4096 * sign(p.x), p.y, p.z)
                best = 4096 - abs(p.x)
            if 0 <= 5120 - abs(p.y) < best:
                np = Vec3(p.x, 5120 * sign(p.y), p.z)
                best = 5120 - abs(p.y)
            return np
        def surface_transition(p1, p2):
            p1 = surface_pos(p1)
            p2 = surface_pos(p2)
            if p1.z == 0:
                if abs(p2.x) == 4096:
                    return Vec3(sign(p2.x) * (4096 + p2.z), p2.y, p1.z)
                elif abs(p2.y) == 5120:
                    return Vec3(p2.x, sign(p2.y) * (5120 + p2.z), p1.z)
            elif abs(p1.x) == 4096:
                if abs(p2.y) == 5120:
                    return Vec3(p1.x, sign(p2.y) * (5120 + abs(p1.x - p2.x)), p2.z)
                elif p2.z == 0:
                    return Vec3(p1.x, p2.y, p2.z - abs(p1.x - p2.x))
            elif abs(p1.y) == 5120:
                if abs(p2.x) == 4096:
                    return Vec3(sign(p2.x) * (4096 + abs(p1.y - p2.y)), p1.y, p2.z)
                elif p2.z == 0:
                    return Vec3(p2.x, p1.y, p2.z - abs(p1.y - p2.y))
            return p2
        # Acceleration Approximations
        # Solve a quadratic equation
        def solve_quadratic(a, b, c, ans, side):
            rt = (ans - c) / a + b**2 / (4 * a**2)
            if rt < 0:
                return None
            else:
                return -b / (2 * a) + math.sqrt(rt) * sign(side)
        # Solve an exponential equation (a - b^cx = ans)
        def solve_exponential(a, b, c, ans):
            return math.log(ans - a, b) / c
        # Get the velocity achieved after a given time
        def velvsacc_to_velvstime(v, t, k, m):
            # Formula: -m/k * (1 - e^(k * t))
            t1 = math.log(-(v / -(m/k) - 1), math.e**k)
            return -m/k * (1 - math.e**(k * (t1 + t)))
        # Get the time taken to change velocity a certain amount
        def velvsacc_changevstime(v, v2, k, m):
            # Formula: -m/k * (1 - e^(k * t))
            v1 = clamp(-(-v * k / m - 1), 0, math.inf)
            v2 = clamp(-(-v2 * k / m - 1), 0, math.inf)
            if v1 > 0 and v2 > 0:
                t1 = math.log(v1, math.e**k)
                t2 = math.log(v2, math.e**k)
                return t2 - t1
            else:
                return math.inf
        # Get the distance covered during car acceleration
        def velvsacc_to_distvstime(v, t, k, m):
            # Formula: -m/k * (1 - e^(k * t))
            t1 = math.log(-(v / -(m/k) - 1), math.e**k)
            int1 = -m/k * (t1 - (math.e**(k * t1)) / k)
            int2 = -m/k * ((t1 + t) - (math.e**(k * (t1 + t))) / k)
            return int2 - int1
        # Get the end velocity given the time (Current Velocity, Throttle Time, Boost Time, Boost Power (default = 1))
        def velvstime(v, t, b, p):
            tb = clamp(b / 100 * 3, 0, t)
            td = t - tb
            nv = v
            # The max speed achieved with boost
            if tb > 0 and nv < 1400:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, tb, -1440 / 1400, 1600 + p * 5950 / 6), 0, 1400)
                tb = clamp(tb - velvsacc_changevstime(temp_v, 1400, -1440 / 1400, 1600 + p * 5950 / 6), 0, math.inf)
            if tb > 0 and nv < 1410:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, tb, -16, 1410 * 16 + p * 5950 / 6), 0, 1410)
                tb = clamp(tb - velvsacc_changevstime(temp_v, 1410, -16, 1410 * 16 + p * 5950 / 6), 0, math.inf)
            if tb > 0 and nv < 2300:
                temp_v = nv
                nv = clamp(nv + p * 5950 / 6 * tb, 0, 2300)
                tb = 0
            # The max speed achieved after boost with throttle
            if td > 0 and nv < 1400:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, td, -1440 / 1400, 1600), 0, 1400)
                td = clamp(td - velvsacc_changevstime(temp_v, 1400, -1440 / 1400, 1600), 0, math.inf)
            if td > 0 and nv < 1410:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, td, -16, 1410 * 16), 0, 1410)
                td = clamp(td - velvsacc_changevstime(temp_v, 1410, -16, 1410 * 16), 0, math.inf)
            return nv
        # Get the end velocity given the time (Current Velocity, Throttle Time, Current Boost, Boost Power (default = 1))
        def distvstime(v, t, b, p):
            tb = clamp(b / 100 * 3, 0, t)
            td = t - tb
            nv = v
            d = 0
            # The max speed achieved with boost
            if tb > 0 and nv < 1400:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, tb, -1440 / 1400, 1600 + p * 5950 / 6), 0, 1400)
                offset = velvsacc_changevstime(temp_v, 1400, -1440 / 1400, 1600 + p * 5950 / 6)
                d += velvsacc_to_distvstime(temp_v, clamp(offset, 0, tb), -1440 / 1400, 1600 + p * 5950 / 6)
                tb = clamp(tb - offset, 0, math.inf)
            if tb > 0 and nv < 1410:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, tb, -16, 1410 * 16 + p * 5950 / 6), 0, 1410)
                offset = velvsacc_changevstime(temp_v, 1410, -16, 1410 * 16 + p * 5950 / 6)
                d += velvsacc_to_distvstime(temp_v, clamp(offset, 0, tb), -16, 1410 * 16 + p * 5950 / 6)
                tb = clamp(tb - offset, 0, math.inf)
            if tb > 0 and nv < 2300:
                temp_v = nv
                nv = clamp(nv + p * 5950 / 6 * tb, 0, 2300)
                t_dif = (nv - temp_v) / (p * 5950 / 6)
                d += temp_v * t_dif + (nv - temp_v) * t_dif / 2 + nv * (tb - t_dif)
                tb = 0
            # The max speed achieved after boost with throttle
            if td > 0 and nv < 1400:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, td, -1440 / 1400, 1600), 0, 1400)
                offset = velvsacc_changevstime(temp_v, 1400, -1440 / 1400, 1600)
                d += velvsacc_to_distvstime(temp_v, clamp(offset, 0, td), -1440 / 1400, 1600)
                td = clamp(td - offset, 0, math.inf)
            if td > 0 and nv < 1410:
                temp_v = nv
                nv = clamp(velvsacc_to_velvstime(nv, td, -16, 1410 * 16), 0, 1410)
                offset = velvsacc_changevstime(temp_v, 1410, -16, 1410 * 16)
                d += velvsacc_to_distvstime(temp_v, clamp(offset, 0, td), -16, 1410 * 16)
                td = clamp(td - offset, 0, math.inf)
                d += nv * td
            if td > 0 and nv >= 1410:
                d += nv * td
            return d
        # Control of aerial (Intended point direction(Vec3), Current point direction(Vec3))
        def aerial_control(front, orig, k):
            car_direction = Vec3(math.cos(orig.yaw) * math.cos(orig.pitch), math.sin(orig.yaw) * math.cos(orig.pitch), math.sin(orig.pitch))
            to_attack = get_aerial_control(front.normalized(), orig)
            # Roll
            '''
            controls.roll = 1
            '''
            # Controls
            p_c = math.cos(to_attack)
            p_y = -math.sin(to_attack)
            # Pitch & Yaw
            return (p_c * math.cos(orig.roll) + p_y * math.sin(orig.roll)) * clamp(front.ang_to(car_direction) * k, -1, 1), (p_y * math.cos(orig.roll) - p_c * math.sin(orig.roll)) * clamp(front.ang_to(car_direction) * k, -1, 1)
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
                return li[smallest], smallest
            pred_x = (4096 - height - pos.x * sign(vel.x)) * safe_div(vel.x) * sign(vel.x)
            pred_y = (5120 - height - pos.y * sign(vel.y)) * safe_div(vel.y) * sign(vel.y)
            pred_z1 = solve_quadratic(-g / 2, vel.z, pos.z, height, 1)
            if pred_z1 == None:
                pred_z1 = 0
            pred_z2 = solve_quadratic(-g / 2, vel.z, pos.z, 2044 - height, -1)
            if pred_z2 == None:
                pred_z2 = math.inf
            return get_smallest([pred_z1, pred_x, pred_y, pred_z2])
        # Get the order in which players would hit the ball
        def get_player_order(li):
            new_li = [[], []]
            for s in range(2):
                for i in range(len(li[s])):
                    car = packet.game_cars[li[s][i]]
                    # Define the car's start in space & time
                    td, bi = next_bounce(Vec3(car.physics.location), Vec3(car.physics.velocity), 20, 650)
                    srp = surface_pos(Vec3(car.physics.location) + Vec3(car.physics.velocity) * td - Vec3(0, 0, 325) * td**2)
                    if abs(srp.z - 1022) == 1022:
                        rv = Vec3(car.physics.velocity).flat()
                    else:
                        if abs(srp.x) == 4096:
                            rv = Vec3(0, car.physics.velocity.y, car.physics.velocity.z - 650 * td)
                        elif abs(srp.y) == 5120:
                            rv = Vec3(car.physics.velocity.x, 0, car.physics.velocity.z - 650 * td)
                    if rv.length() > 2300:
                        rv = rv.rescale(2300)
                    # Scroll through the timeline to determine the car's next possible ball collision
                    t = td
                    while t <= 5:
                        bp = predict_ball(t)
                        max_height = bp.physics.location.z + bp.physics.velocity.z**2 / 1300
                        max_ball_vel = Vec3(bp.physics.velocity.x, bp.physics.velocity.y, -math.sqrt(abs(max_height - 92.75) / 325))
                        b_offset = surface_pos(Vec3(bp.physics.location)) - Vec3(bp.physics.location)
                        jt, ja = jump_time_x(b_offset.length(), math.cos(b_offset.ang_to(Vec3(0, 0, -1))) * 650, True)
                        dt = distvstime(Vec3(car.physics.velocity).length(), t - td - jt, car.boost, 1) + velvstime(Vec3(car.physics.velocity).length(), t - td - jt, car.boost, 1) * jt
                        target_dist = surface_transition(srp, Vec3(bp.physics.location)).dist(Vec3(car.physics.location))
                        if target_dist > dt:
                            t += max(math.floor(((target_dist - dt) / (max_ball_vel.length() + min(1410 + car.boost * 119 / 4, 2300))) * 60) / 60, 1 / 60)
                        else:
                            if t <= 5:
                                new_li[s].append(t)
                            break
                    if t > 5:
                        new_li[s].append(t)
            return new_li
        # Get the nearest player of a team to the ball
        def nearest_player(players, orders, teams):
            best_t = math.inf
            best_i = 0
            for i2 in range(len(players[teams])):
                if orders[teams][i2] < best_t:
                    best_t = orders[teams][i2]
                    best_i = players[teams][i2]
            return packet.game_cars[best_i], best_t
        # Get the most threatening player for a flick
        def flick_threats(players, teams):
            best_t = math.inf
            best_i = 0
            for i2 in range(len(players[teams])):
                p = packet.game_cars[players[teams][i2]]
                new_t = ((Vec3(p.physics.location) - ball_location).flat().length() + 92.75) * safe_div((Vec3(p.physics.velocity) - ball_velocity).flat().length() + 292 * bool(not p.double_jumped))
                if new_t < best_t:
                    best_t = new_t
                    best_i = players[teams][i2]
            return packet.game_cars[best_i], best_t
        # Get the max jump height
        def jump_time_x(h, g, double):
            def fx(x):
                return (292 * 5 - g) / 2 * x**2 + 292 * x
            def hx(x):
                return -g / 2 * x**2 + 584 * x - 292 / 10
            def qx(x):
                return -g / 2 * x**2 + 876 * x - (365 / 3 - 292 / 10)
            if h <= fx(12 / 60):
                return solve_quadratic((292 * 5 - g) / 2, 292, 0, h, 1), 1
            elif h <= qx(876 / g) and double:
                return solve_quadratic(-g / 2, 876, -(365 / 3 - 292 / 10), h, -1), 2
            elif h <= hx(584 / g):
                return solve_quadratic(-g / 2, 584, -292 / 10, h, -1), 1
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
        def aerial_dist(t, boost):
            return 5950 / 12 * min(t, boost * 3 / 100)**2 + 5950 / 6 * boost * 3 / 100 * max(t - boost * 3 / 100, 0)
        def air_pos(loc, vel, t):
            return loc + vel * t + Vec3(0, 0, -325) * t**2
        def aerial_dir():
            for i in range(1, 301):
                t = i / 60
                b = predict_ball(t)
                bp = Vec3(b.physics.location)
                offsetog = bp - (car_location * t - Vec3(0, 0, 325) * t**2)
                mv = (car_velocity + car_direction * car_direction.ang_to(offsetog) / math.pi * 1000 * bool(my_car.has_wheel_contact))
                offset = bp - (car_location + mv.rescale(min(mv.length(), 2300)) * t - Vec3(0, 0, 325) * t**2)
                if aerial_dist(t, my_car.boost) > offset.length():
                    return t
            return 301 / 60
        # Directions
        def circle_dir(pitch, yaw, roll):
            cp = math.cos(pitch)
            cy = math.cos(yaw)
            cr = math.cos(-roll)
            sp = math.sin(pitch)
            sy = math.sin(yaw)
            sr = math.sin(-roll)
            return Vec3(sy * sr - cy * sp * cr, -cy * sr - sy * sp * cr, cp * cr)
        def to_right(pos):
            return Vec3(-pos.y, pos.x, pos.z)
        def to_left(pos):
            return Vec3(pos.y, -pos.x, pos.z)
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
        # Get the distance required assuming a circular arc at the end
        def dtd_dist(pos, vel):
            # Important values
            tv = vel.length()
            r = 12500 / 11
            # Vectors of the target and the direction of it
            dp1 = surface_transition(car_location, pos)
            dp2 = surface_transition(car_location, pos + vel.normalized())
            offset = dp1 - surface_pos(car_location)
            tdir = (dp2 - dp1).normalized()
            cf = surface_pos(car_location)
            # Get the position of the circle
            if dp1.z == 0:
                steer_dir = sign(tdir.dist(Vec3(offset.y, -offset.x, 0)) - tdir.dist(Vec3(-offset.y, offset.x, 0)))
            elif abs(dp1.x) == 4096:
                steer_dir = sign(tdir.dist(Vec3(0, -offset.z, offset.y)) - tdir.dist(Vec3(0, offset.z, -offset.y)))
            elif abs(dp1.y) == 5120:
                steer_dir = sign(tdir.dist(Vec3(-offset.z, 0, offset.x)) - tdir.dist(Vec3(offset.z, 0, -offset.x)))
            if dp1.z == 0:
                circle_pos = dp1 + Vec3(-tdir.y, tdir.x, 0).rescale(r * steer_dir)
            elif abs(dp1.x) == 4096:
                circle_pos = dp1 + Vec3(0, tdir.z, -tdir.y).rescale(r * steer_dir)
            elif abs(dp1.y) == 5120:
                circle_pos = dp1 + Vec3(tdir.z, 0, -tdir.x).rescale(r * steer_dir)
            # Get the angles
            d_dev = (surface_pos(circle_pos) - cf)
            if d_dev.length() > r:
                a_dev = math.atan(math.sqrt(r**2 / (d_dev.length()**2 - r**2)))
                if abs(dp1.x) == 4096:
                    oa = math.atan2(d_dev.z, d_dev.y)
                    tl = cf + Vec3(0, math.cos(oa - a_dev * steer_dir), math.sin(oa - a_dev * steer_dir)) * d_dev.length()
                elif abs(dp1.y) == 5120:
                    oa = math.atan2(d_dev.z, d_dev.x)
                    tl = cf + Vec3(math.cos(oa - a_dev * steer_dir), 0, math.sin(oa - a_dev * steer_dir)) * d_dev.length()
                else:
                    oa = math.atan2(d_dev.y, d_dev.x)
                    tl = cf + Vec3(math.cos(oa - a_dev * steer_dir), math.sin(oa - a_dev * steer_dir), 0) * d_dev.length()
                straight_d = math.sqrt((d_dev.length() - r * math.sin(math.atan(a_dev)))**2 + (r * math.cos(math.atan(a_dev)))**2)
                return straight_d + math.asin((d_dev + cf).dist(tl) / r / 2) * 2 * r
            else:
                return (surface_pos(pos) - surface_pos(circle_pos)).ang_to(-d_dev) * min(r, d_dev.length()) + max(0, r - d_dev.length())
        '''
        Algorithms
        '''
        def fast_turn(tl):
            controls.handbrake = Vec3(my_car.physics.angular_velocity).length() > 2 and car_direction.ang_to(tl - car_location) >= math.pi / 2 and car_direction.ang_to(car_velocity) < math.pi / 4
        # Drive to a point but hit from a specific angle (Safe up to 1600, Fatal beyond 2000)
        def drive_to_dir(pos, vel):
            # Important values
            tv = vel.length()
            r = 12500 / 11
            # Vectors of the target and the direction of it
            dp1 = surface_transition(car_location, pos)
            dp2 = surface_transition(car_location, pos + vel.normalized())
            offset = dp1 - surface_pos(car_location)
            tdir = (dp2 - dp1).normalized()
            # Get the position of the circle
            if dp1.z == 0:
                steer_dir = sign(tdir.dist(Vec3(offset.y, -offset.x, 0)) - tdir.dist(Vec3(-offset.y, offset.x, 0)))
            elif abs(dp1.x) == 4096:
                steer_dir = sign(tdir.dist(Vec3(0, -offset.z, offset.y)) - tdir.dist(Vec3(0, offset.z, -offset.y)))
            elif abs(dp1.y) == 5120:
                steer_dir = sign(tdir.dist(Vec3(-offset.z, 0, offset.x)) - tdir.dist(Vec3(offset.z, 0, -offset.x)))
            if dp1.z == 0:
                circle_pos = dp1 + Vec3(-tdir.y, tdir.x, 0).rescale(r * steer_dir)
            elif abs(dp1.x) == 4096:
                circle_pos = dp1 + Vec3(0, tdir.z, -tdir.y).rescale(r * steer_dir)
            elif abs(dp1.y) == 5120:
                circle_pos = dp1 + Vec3(tdir.z, 0, -tdir.x).rescale(r * steer_dir)
            # Get the angles
            d_dev = (circle_pos - surface_pos(car_location))
            if d_dev.length() > r + 300:
                a_dev = math.atan(math.sqrt(r**2 / (d_dev.length()**2 - r**2)))
                if abs(dp1.x) == 4096:
                    oa = math.atan2(d_dev.z, d_dev.y)
                    tl = car_location + Vec3(0, math.cos(oa - a_dev * steer_dir), math.sin(oa - a_dev * steer_dir)) * d_dev.length()
                elif abs(dp1.y) == 5120:
                    oa = math.atan2(d_dev.z, d_dev.x)
                    tl = car_location + Vec3(math.cos(oa - a_dev * steer_dir), 0, math.sin(oa - a_dev * steer_dir)) * d_dev.length()
                else:
                    oa = math.atan2(d_dev.y, d_dev.x)
                    tl = car_location + Vec3(math.cos(oa - a_dev * steer_dir), math.sin(oa - a_dev * steer_dir), 0) * d_dev.length()
                controls.steer = steer_toward_target(my_car, tl) + steer_toward_target(my_car, circle_pos) * clamp(1 + (r - d_dev.length()) / 100, 0, 1)
            else:
                ang_k = (car_velocity.length() / (r * 2 * math.pi) - Vec3(my_car.physics.angular_velocity).length())
                orig_ang = car_direction.ang_to(d_dev) - math.pi / 2
                if d_dev.length() - r >= 0:
                    k = clamp(car_direction.ang_to(d_dev - car_direction.rescale(car_velocity.length() / 5 * max((r - d_dev.length()) / 100, 0))) - math.pi / 2 + 0.05 + (d_dev.length() - r + car_velocity.length()**2 / 120000) / 500, 0, 0.1) * 10
                else:
                    k = clamp(car_direction.ang_to(d_dev) - math.pi / 2, 0, 0.1) * 10
                tl = circle_pos
                controls.steer = steer_toward_target(my_car, tl) * k
            # Controls
            controls.throttle = sign(vel.length() - car_velocity.length())
            controls.boost = car_velocity.length() < vel.length()
            # Draw
            for i in range(90):
                self.renderer.draw_line_3d(circle_pos + Vec3(r * math.cos(math.pi / 45 * i), r * math.sin(math.pi / 45 * i), 20), circle_pos + Vec3(r * math.cos(math.pi / 45 * (i + 1)), r * math.sin(math.pi / 45 * (i + 1)), 20), self.renderer.white())
            self.renderer.draw_line_3d(car_location, tl, self.renderer.blue())
            self.renderer.draw_rect_3d(dp1, 8, 8, True, self.renderer.cyan(), centered=True)
            self.renderer.draw_rect_3d(circle_pos, 8, 8, True, self.renderer.red(), centered=True)
        '''
        Selectors
        '''
        def dribble_selector():
            if packet.game_info.is_kickoff_pause == True:
                tl = kickoff()
            elif ball_location.z + ball_velocity.z**2 / 1300 < 110:
                tl = lift_ball()
            elif (ball_location - car_location).flat().length() < 100 and (ball_velocity.length() > 700 and ball_velocity.flat().ang_to((send_location - ball_location).flat()) >= math.pi / 6 or ball_location.z > 120 and (car_location.dist(send_location) >= Vec3(nearest_enemy.physics.location).dist(send_location) or nearest_tt < 1)):
                if nearest_tt < 1 and distvstime(Vec3(nearest_threat.physics.velocity).length(), car_location.flat().dist(send_location) / 1200, nearest_threat.boost, 1) >= car_location.flat().dist(send_location):
                    tl = carry_flick()
                else:
                    tl = catch()
            else:
                tl = dribble_accelerate()
            return tl
        def hit_selector():
            tl = hard_hit()
            return tl
        '''
        Finished Modes
        '''
        # Kickoff
        def kickoff():
            tl = ball_location - send_location.rescale(92.75 / 2)
            controls.throttle = 1
            controls.boost = True
            controls.steer = steer_toward_target(my_car, tl)
            if 1100 > car_velocity.length() > 1000:
                override = self.speed_flip(packet, sign(car_location.x * send_location.y))
            elif (tl - car_location).flat().length() < car_velocity.length() * 0.2 and my_car.has_wheel_contact == True:
                self.jump_time = 5
                self.jump_dir = Vec3(0, 0, 0)
            self.renderer.draw_string_3d(car_location, 1, 1, "Kickoff", self.renderer.red())
            return tl
        # Control the ball's velocity
        def lift_ball():
            o_offset = math.cos(car_direction.ang_to((ball_location - car_location).flat())) * (ball_location - car_location).flat().length()
            f_offset = o_offset - (100 - car_velocity.length() / 10)
            tl = ball_location + sign((car_location - side_direction).flat().dist(ball_location.flat()) - (car_location + side_direction).flat().dist(ball_location.flat())) * Vec3(car_direction.y, -car_direction.x, 0).rescale((130 - max(10 - ball_velocity.length() / 20, 0) - (ball_location.z + ball_velocity.z**2 / 1300 - 92.75) * 2 * bool(f_offset < 15)) * bool(f_offset >= 0)) + car_direction.flat().rescale(50)
            if (car_location - ball_location).flat().length() < 130 or math.cos(car_direction.ang_to((ball_location - car_location).flat())) >= 0:
                controls.throttle = sign(f_offset + 30 + (ball_location.z - 92.75) - brake_distance(car_velocity.flat().length(), ball_velocity.flat().length(), 3500))
            else:
                controls.throttle = 1
            if (car_location - ball_location).flat().length() > 130:
                fast_turn(tl)
            if car_velocity.length() < ball_velocity.length() and math.cos(car_direction.ang_to((ball_location - car_location).flat())) * (ball_location - car_location).flat().length() > 0 and controls.throttle == -1:
                controls.throttle = 0
            controls.steer = steer_toward_target(my_car, tl)
            self.renderer.draw_string_3d(car_location, 1, 1, "Lift Ball", self.renderer.red())
            return tl
        # Send the ball into the net hard while carrying
        def dribble_accelerate():
            carry_bounce_index = 5
            prev_bounce = 0
            bp = predict_ball(prev_bounce)
            while carry_bounce_index != 0 and prev_bounce < 5:
                carry_bounce, carry_bounce_index = next_bounce(Vec3(bp.physics.location), Vec3(bp.physics.velocity), 92.75 + 18, 650)
                prev_bounce += max(carry_bounce, 1 / 60)
                bp = predict_ball(prev_bounce)
            bpos = Vec3(bp.physics.location).flat()
            bsv = ball_velocity.flat()
            tl1 = bpos + Vec3(-bsv.y, bsv.x, 0).rescale(clamp(clamp(400 * bsv.ang_to(send_location - ball_location.flat()) * sign(Vec3(-bsv.y, bsv.x, 0).dist(send_location - ball_location.flat()) - Vec3(bsv.y, -bsv.x, 0).dist(send_location - ball_location.flat())), -60, 60), -bsv.ang_to((send_location - car_location).flat()) * 100, bsv.ang_to((send_location - car_location).flat()) * 100))
            tl2 = car_location + (bpos - send_location)
            tlopttime = (math.pi / 2 - car_direction.ang_to(car_velocity)) / 2 + car_velocity.length() / 3500
            tlopt = distvstime(0, max(prev_bounce - tlopttime, 0), 0, 1) >= surface_pos(car_location + car_velocity.rescale(car_velocity.length() * (math.pi / 2 - car_direction.ang_to(car_velocity)) / 2 + car_velocity.length()**2 / 7000)).dist(surface_pos(tl1))
            tl = tl2 * bool(tlopt) + tl1 * bool(not tlopt)
            if ball_location.z + ball_velocity.z**2 / 1300 >= 140 or ball_velocity.flat().ang_to((send_location - ball_location).flat()) >= math.pi / 6:
                controls.throttle = sign(car_location.flat().dist(tl) - car_velocity.flat().length() * prev_bounce)
                self.renderer.draw_string_3d(car_location, 1, 1, "Dribble Accelerate", self.renderer.green())
            else:
                controls.throttle = sign((car_location - ball_location).flat().length() - 90 + bsv.length() - car_velocity.flat().length())
                self.renderer.draw_string_3d(car_location, 1, 1, "Dribble Accelerate", self.renderer.red())
            fast_turn(tl)
            controls.boost = 210 > (car_location - ball_location).flat().length() > 90 and car_velocity.length() <= 2290 and ball_location.z + ball_velocity.z**2 / 1300 < 140 and car_direction.ang_to(ball_location - car_location) < math.pi / 2
            controls.steer = steer_toward_target(my_car, tl)
            return tl
        # Catch the ball
        def catch():
            # Predict where the bounce will take place
            carry_bounce_index = 5
            prev_bounce = 0
            bp = predict_ball(prev_bounce)
            while carry_bounce_index != 0 and prev_bounce < 5:
                carry_bounce, carry_bounce_index = next_bounce(Vec3(bp.physics.location), Vec3(bp.physics.velocity), 92.75 + 18, 650)
                prev_bounce += max(carry_bounce, 1 / 60)
                bp = predict_ball(prev_bounce)
            # Variables
            bpos = Vec3(bp.physics.location).flat()
            g_offset = bpos - send_location
            bsv = Vec3(bp.physics.velocity).flat()
            csv = car_velocity.flat()
            tvel = 1000
            hbv = (bsv - csv).length() * math.cos((bsv - csv).ang_to(Vec3(-car_direction.y, car_direction.x, 0)))
            vbv = bsv.length() * math.cos(bsv.ang_to(car_direction))
            # Where to go
            togo = send_location
            redirect_angle = bsv.ang_to(togo - bpos) * sign(Vec3(-bsv.y, bsv.x, 0).dist(togo - ball_location.flat()) - Vec3(bsv.y, -bsv.x, 0).dist(togo - ball_location.flat()))
            ang_limit = math.pi * clamp((ball_velocity.flat().length() - 300) / 700, 0, 1)
            bounce_angle = clamp(redirect_angle, -ang_limit, ang_limit)
            # Target
            v_offset = min((vbv - tvel * math.cos(bounce_angle)) / 10 / (1 + abs(bp.physics.velocity.z) / 500), 80)
            h_offset = min((hbv + tvel * math.sin(bounce_angle)) / 10 / (1 + abs(bp.physics.velocity.z) / 500), 70)
            tl = bpos + car_direction.rescale(v_offset) + Vec3(-car_direction.y, car_direction.x).rescale(h_offset)
            controls.throttle = sign(car_location.flat().dist(tl) - car_velocity.flat().length() * prev_bounce)
            fast_turn(tl)
            controls.steer = steer_toward_target(my_car, tl)
            self.renderer.draw_string_3d(car_location, 1, 1, "Catch", self.renderer.white())
            return tl
        # Carry & Flick
        def carry_flick():
            carry_bounce_index = 5
            prev_bounce = 0
            bp = predict_ball(prev_bounce)
            while carry_bounce_index != 0 and prev_bounce < 5:
                carry_bounce, carry_bounce_index = next_bounce(Vec3(bp.physics.location), Vec3(bp.physics.velocity), 92.75 + 18, 650)
                prev_bounce += max(carry_bounce, 1 / 60)
                bp = predict_ball(prev_bounce)
            bpos = Vec3(bp.physics.location).flat()
            bsv = ball_velocity.flat()
            tl = bpos - bsv.rescale(clamp((70 - bsv.length() / 10) / (1 + abs(bp.physics.velocity.z) / 500), -70, 70)) + Vec3(-bsv.y, bsv.x, 0).rescale(bsv.ang_to(send_location - bpos) * 50 / (1 + abs(bp.physics.velocity.z) / 500) * clamp(nearest_tt - 0.5, 0, 1) / math.pi * sign(Vec3(-bsv.y, bsv.x, 0).dist(send_location - ball_location.flat()) - Vec3(bsv.y, -bsv.x, 0).dist(send_location - ball_location.flat())))
            throttle_f = car_location.flat().dist(tl) - car_velocity.flat().length() * prev_bounce
            if (ball_velocity - car_velocity).flat().length() < 30 and ball_location.z < 140:
                controls.throttle = bool(throttle_f > 0)
                self.renderer.draw_string_3d(car_location, 1, 1, "Carry & Flick", self.renderer.red())
            else:
                controls.throttle = sign(throttle_f)
                self.renderer.draw_string_3d(car_location, 1, 1, "Carry & Flick", self.renderer.green())
            fast_turn(tl)
            controls.steer = steer_toward_target(my_car, tl)
            if nearest_tt <= 0.5 and bool(my_car.has_wheel_contact) >= bool(nearest_enemy.has_wheel_contact) and self.jump_time == 0 and (ball_location - car_location).flat().length() <= 100 and (ball_velocity - car_velocity).length() <= 100:
                self.jump_time = 12
            if self.jump_time > 0:
                self.jump_dir = Vec3(random.randint(-1, 1), random.randint(-1, 1), 0) * bool(ball_location.z - car_location.z < 130)
            return tl
        # Fly in the air to hit the ball
        def aerial():
            b = predict_ball(aerial_t)
            bp = Vec3(b.physics.location)
            offsetog = bp - (car_location * aerial_t - Vec3(0, 0, 325) * aerial_t**2)
            mv = (car_velocity + car_direction * car_direction.ang_to(offsetog) / math.pi * 1000 * bool(False))
            offset = bp - (car_location + mv.rescale(min(mv.length(), 2300)) * aerial_t - Vec3(0, 0, 325) * aerial_t**2)
            aerial_front = offset
            if my_car.has_wheel_contact == True:
                tl = Vec3(predict_ball(aerial_t).physics.location)
            else:
                tl = car_location + offset
            rot_vel = [(car_rotation.pitch - self.prev_rot[0]) * 60, yaw_conversion(self.prev_rot[1], car_rotation.yaw) * 60 * math.cos(car_rotation.pitch), roll_conversion(self.prev_rot[2], car_rotation.roll) * 60]
            fast_turn(tl)
            dt = surface_pos(car_location + offset.normalized()) - surface_pos(car_location)
            prev_ang = (surface_pos(car_location + car_dir(self.prev_rot[0], self.prev_rot[1])) - surface_pos(car_location)).ang_to(dt)
            curr_ang = (surface_pos(car_location + car_direction) - surface_pos(car_location)).ang_to(dt)
            if abs(curr_ang) < 0.1 + 0.2 * (prev_ang - curr_ang) * bool(prev_ang - curr_ang > 0):
                if self.jump_time == 0 and (bp.dist(car_location + (car_velocity + roof_direction * 292) * aerial_t - Vec3(0, 0, 325) * aerial_t**2) < bp.dist(car_location + car_velocity * aerial_t - Vec3(0, 0, 325) * aerial_t**2) or my_car.has_wheel_contact == True):
                    self.jump_time = 12
            vd_pitch, vd_yaw = aerial_control(aerial_front, car_rotation, 1)
            c_pitch = vd_pitch - math.sqrt(abs(rot_vel[0]) / 6.23) * sign(rot_vel[0]) * math.cos(car_rotation.roll - rot_vel[2] / 120) - math.sqrt(abs(rot_vel[1]) / 6.23) * sign(rot_vel[1]) * math.sin(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch)
            c_yaw = vd_yaw - math.sqrt(abs(rot_vel[1]) / 4.555) * sign(rot_vel[1]) * math.cos(car_rotation.roll - rot_vel[2] / 120) * math.cos(car_rotation.pitch) - math.sqrt(abs(rot_vel[0]) / 4.555) * sign(rot_vel[0]) * -math.sin(car_rotation.roll - rot_vel[2] / 120)
            if abs(c_pitch) > abs(c_yaw):
                c_pitch, c_yaw = c_pitch / abs(c_pitch), c_yaw / abs(c_pitch)
            elif abs(c_yaw) > abs(c_pitch):
                c_pitch, c_yaw = c_pitch / abs(c_yaw), c_yaw / abs(c_yaw)
            # Controls
            controls.pitch, controls.yaw = c_pitch, c_yaw
            controls.boost = not my_car.has_wheel_contact
            if my_car.has_wheel_contact == True:
                controls.throttle = sign((surface_pos(car_location + offset.normalized()) - surface_pos(car_location)).length() * offset.length() - car_velocity.length() * aerial_t)
            else:
                controls.throttle = 1
            controls.steer = steer_toward_target(my_car, tl)
            self.renderer.draw_string_3d(car_location, 1, 1, "Aerial", self.renderer.white())
            return ball_location
        # Prepare to beat the opponent in the air
        def aerial_beat_setup():
            b = predict_ball(aerial_t)
            bp = Vec3(b.physics.location)
            offsetog = bp - (car_location * aerial_t - Vec3(0, 0, 325) * aerial_t**2)
            mv = (car_velocity + car_direction * car_direction.ang_to(offsetog) / math.pi * 1000 * bool(False))
            offset = bp - (car_location + mv.rescale(min(mv.length(), 2300)) * aerial_t - Vec3(0, 0, 325) * aerial_t**2)
            aerial_front = offset
            tl = Vec3(predict_ball(aerial_t).physics.location)
            rot_vel = [(car_rotation.pitch - self.prev_rot[0]) * 60, yaw_conversion(self.prev_rot[1], car_rotation.yaw) * 60 * math.cos(car_rotation.pitch), roll_conversion(self.prev_rot[2], car_rotation.roll) * 60]
            fast_turn(tl)
            controls.steer = steer_toward_target(my_car, tl)
            controls.throttle = sign((surface_pos(car_location + offset.normalized()) - surface_pos(car_location)).length() * offset.length() - car_velocity.length() * aerial_t)
            if nearest_enemy.has_wheel_contact == False and aerial_dist(aerial_t, nearest_enemy.boost) - (Vec3(nearest_enemy.physics.location) + Vec3(nearest_enemy.physics.velocity) * aerial_t + Vec3(0, 0, -325) * aerial_t**2).dist(tl) < aerial_dist(aerial_t, my_car.boost) - (car_location + (car_velocity + roof_direction * 292 * bool(my_car.has_wheel_contact)) * aerial_t + Vec3(0, 0, -325) * aerial_t**2).dist(tl):
                return aerial()
            else:
                return tl
        # Hard Hit
        def hard_hit():
            tl = surface_pos(predict_ball(nearest_st).physics.location)
            fast_turn(tl)
            controls.throttle = sign((surface_pos(car_location + offset.normalized()) - surface_pos(car_location)).length() * offset.length() - car_velocity.length() * aerial_t)
            return tl
        '''
        Indev
        '''
        my_car = packet.game_cars[self.index]
        ball_prediction = self.get_ball_prediction_struct()
        player_list, car_index = get_players(packet)
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        car_rotation = my_car.physics.rotation
        car_direction = car_dir(car_rotation.pitch, car_rotation.yaw)
        side_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll + math.pi / 2)
        roof_direction = circle_dir(car_rotation.pitch, car_rotation.yaw, car_rotation.roll)
        player_orders = get_player_order(player_list)
        nearest_friendly, nearest_ft = nearest_player(player_list, player_orders, self.team)
        nearest_enemy, nearest_et = nearest_player(player_list, player_orders, 1 - self.team)
        nearest_st = player_orders[self.team][car_index]
        aerial_t = aerial_dir()
        aerial_eligible = aerial_t <= 5
        send_location = Vec3(0, 5120 * sign(0.5 - self.team), 0)
        ball_location = Vec3(packet.game_ball.physics.location)
        ball_velocity = Vec3(packet.game_ball.physics.velocity)
        nearest_threat, nearest_tt = flick_threats(player_list, 1 - self.team)
        bounce, bounce_index = next_bounce(ball_location, ball_velocity, 92.75, 650)
        e_angle = (surface_pos(Vec3(predict_ball(nearest_et).physics.location)) - surface_pos(Vec3(nearest_enemy.physics.location))).ang_to(-send_location - surface_pos(Vec3(predict_ball(nearest_et).physics.location)))
        e_carry = (Vec3(nearest_enemy.physics.location) - ball_location).flat().length() <= 100 and 0 < ball_location.z - nearest_enemy.physics.location.z < 150
        
        controls = SimpleControllerState()
        override = None
        # Carry algorithms
        target_location = dribble_selector()
        '''
        if (ball_location - car_location).flat().length() < 100 and ball_velocity.length() > 700 and ball_velocity.flat().ang_to((send_location - ball_location).flat()) >= math.pi / 6:
            target_location = catch()
        else:
            target_location = dribble_accelerate()
        '''
        '''
        if Vec3(nearest_enemy.physics.location).dist(send_location) > car_location.dist(send_location) and nearest_ft < nearest_et > 1 and ball_location.z < 120 and ball_velocity.z < 20:
            target_location = dribble_accelerate()
        elif (car_location - Vec3(predict_ball(bounce).physics.location)).flat().length() > distvstime(car_velocity.length(), bounce, 0, bounce) and not (car_location.flat() - ball_location.flat()).length() <= 100 + min(ball_location.z - 92.75, 100) or nearest_et < bounce or nearest_et < nearest_ft + 0.2 or (abs(predict_ball(nearest_ft).physics.location.x) >= 3976 or abs(predict_ball(nearest_ft).physics.location.y) >= 5000) or abs(ball_location.x) > 893 and abs(predict_ball(nearest_ft).physics.location.x) <= 893 and sign(car_location.y - predict_ball(nearest_ft).physics.location.y) == sign(predict_ball(nearest_ft).physics.location.y + send_location.y):
            target_location = hard_hit()
        elif ball_velocity.flat().ang_to((send_location - ball_location).flat()) <= 0.1 or nearest_et < 1:  
            target_location = carry_flick()
        else:
            target_location = catch()
        '''
        if self.jump_time == 13:
            self.jump_time = 2
        self.jump_time = clamp(self.jump_time - 1, 0, 84)
        self.flip_time = clamp(self.flip_time - 1, 0, 48)
        controls.jump = self.jump_time != 13 and self.jump_time != 0
        if controls.jump == True:
            controls.pitch = self.jump_dir.x
            controls.yaw = self.jump_dir.y
            controls.roll = self.jump_dir.z
            if self.jump_dir != Vec3(0, 0, 0) and my_car.double_jumped == False:
                self.flip_time = 48
        self.prev_rot = [car_rotation.pitch, car_rotation.yaw, car_rotation.roll]
        if override:
            return override
        else:
            return controls

    def begin_front_flip(self, packet):
        # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.1, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=1 / 60, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=1 / 60, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)

    def double_jump(self, packet):
        # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=1 / 60, controls=SimpleControllerState(jump = False, pitch = 0, yaw = 0, roll = 0)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump = True, pitch = 0, yaw = 0, roll = 0)),
            ControlStep(duration=1 / 60, controls=SimpleControllerState(jump = False, pitch = 0, yaw = 0, roll = 0)),
            ControlStep(duration=1 / 60, controls=SimpleControllerState(jump = True, pitch = 0, yaw = 0, roll = 0))
        ])

        # Return the controls associated with the beginning of the sequence so we can start right away.
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
