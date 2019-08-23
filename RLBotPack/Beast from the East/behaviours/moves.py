import math
import time

from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.dodge import DodgeManeuver
from maneuvers.recovery import RecoveryManeuver
from maneuvers.small_jump import SmallJumpManeuver
from util import rendering
from util.curves import curve_from_arrival_dir
from util.info import Field, Ball, is_near_wall
from util.predict import ball_predict, next_ball_landing
from util.rlmath import lerp, sign, clip, fix_ang
from util.vec import Vec3, angle_between, xy, dot, norm, proj_onto_size, normalize


class DriveController:
    def __init__(self):
        self.controls = SimpleControllerState()
        self.dodge = None
        self.last_point = None
        self.last_dodge_end_time = 0
        self.dodge_cooldown = 0.26
        self.recovery = None

    def start_dodge(self, bot):
        if self.dodge is None:
            self.dodge = DodgeManeuver(bot, self.last_point)

    def go_towards_point(self, bot, point: Vec3, target_vel=1430, slide=False, boost_min=101, can_keep_speed=True, can_dodge=True, wall_offset_allowed=110) -> SimpleControllerState:
        REQUIRED_ANG_FOR_SLIDE = 1.65
        REQUIRED_VELF_FOR_DODGE = 1100

        car = bot.info.my_car

        # Dodge is done
        if self.dodge is not None and self.dodge.done:
            self.dodge = None
            self.last_dodge_end_time = bot.info.time

        # Continue dodge
        if self.dodge is not None:
            self.dodge.target = point
            return self.dodge.exec(bot)

        # Begin recovery
        if not car.on_ground:
            bot.maneuver = RecoveryManeuver(bot)
            return self.controls

        # Get down from wall by choosing a point close to ground
        if not is_near_wall(point, wall_offset_allowed) and angle_between(car.up, Vec3(0, 0, 1)) > math.pi * 0.31:
            point = lerp(xy(car.pos), xy(point), 0.5)

        # If the car is in a goal, avoid goal posts
        self.avoid_goal_post(bot, point)

        car_to_point = point - car.pos

        # The vector from the car to the point in local coordinates:
        # point_local.x: how far in front of my car
        # point_local.y: how far to the left of my car
        # point_local.z: how far above my car
        point_local = dot(point - car.pos, car.rot)

        # Angle to point in local xy plane and other stuff
        angle = math.atan2(point_local.y, point_local.x)
        dist = norm(point_local)
        vel_f = proj_onto_size(car.vel, car.forward)
        vel_towards_point = proj_onto_size(car.vel, car_to_point)

        # Start dodge
        if can_dodge and abs(angle) <= 0.02 and vel_towards_point > REQUIRED_VELF_FOR_DODGE\
                and dist > vel_towards_point + 500 + 700 and bot.info.time > self.last_dodge_end_time + self.dodge_cooldown:
            self.dodge = DodgeManeuver(bot, point)

        # Is in turn radius deadzone?
        tr = turn_radius(abs(vel_f + 50))  # small bias
        tr_side = sign(angle)
        tr_center_local = Vec3(0, tr * tr_side, 0)
        point_is_in_turn_radius_deadzone = norm(point_local - tr_center_local) < tr
        # Draw turn radius deadzone
        if car.on_ground and bot.do_rendering:
            tr_center_world = car.pos + dot(car.rot, tr_center_local)
            tr_center_world_2 = car.pos + dot(car.rot, -1 * tr_center_local)
            rendering.draw_circle(bot, tr_center_world, car.up, tr, 22)
            rendering.draw_circle(bot, tr_center_world_2, car.up, tr, 22)

        if point_is_in_turn_radius_deadzone:
            # Hard turn
            self.controls.steer = sign(angle)
            self.controls.boost = False
            self.controls.throttle = 0 if vel_f > 150 else 0.1
            if point_local.x < 25:
                # Brake or go backwards when the point is really close but not in front of us
                self.controls.throttle = clip((25 - point_local.x) * -.5, 0, -0.6)
                self.controls.steer = 0
                if vel_f > 300:
                    self.controls.handbrake = True

        else:
            # Should drop speed or just keep up the speed?
            if can_keep_speed and target_vel < vel_towards_point:
                target_vel = vel_towards_point
            else:
                # Small lerp adjustment
                target_vel = lerp(vel_towards_point, target_vel, 1.2)

            # Turn and maybe slide
            self.controls.steer = clip(angle + (2.5*angle) ** 3, -1.0, 1.0)
            if slide and abs(angle) > REQUIRED_ANG_FOR_SLIDE:
                self.controls.handbrake = True
                self.controls.steer = sign(angle)
            else:
                self.controls.handbrake = False

            # Overshoot target vel for quick adjustment
            target_vel = lerp(vel_towards_point, target_vel, 1.2)

            # Find appropriate throttle/boost
            if vel_towards_point < target_vel:
                self.controls.throttle = 1
                if boost_min < car.boost and vel_towards_point + 25 < target_vel and target_vel > 1400 \
                        and not self.controls.handbrake and is_heading_towards(angle, dist):
                    self.controls.boost = True
                else:
                    self.controls.boost = False

            else:
                vel_delta = target_vel - vel_towards_point
                self.controls.throttle = clip(0.2 + vel_delta / 500, 0, -1)
                self.controls.boost = False
                if self.controls.handbrake:
                    self.controls.throttle = min(0.4, self.controls.throttle)

        # Saved if something outside calls start_dodge() in the meantime
        self.last_point = point

        return self.controls

    def avoid_goal_post(self, bot, point):
        car = bot.info.my_car
        car_to_point = point - car.pos

        # Car is not in goal, not adjustment needed
        if abs(car.pos.y) < Field.LENGTH / 2:
            return

        # Car can go straight, not adjustment needed
        if car_to_point.x == 0:
            return

        # Do we need to cross a goal post to get to the point?
        goalx = Field.GOAL_WIDTH / 2 - 100
        goaly = Field.LENGTH / 2 - 100
        t = max((goalx - car.pos.x) / car_to_point.x,
                (-goalx - car.pos.x) / car_to_point.x)
        # This is the y coordinate when car would hit a goal wall. Is that inside the goal?
        crossing_goalx_at_y = abs(car.pos.y + t * car_to_point.y)
        if crossing_goalx_at_y > goaly:
            # Adjustment is needed
            point.x = clip(point.x, -goalx, goalx)
            point.y = clip(point.y, -goaly, goaly)
            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, point, bot.renderer.green())

    def go_home(self, bot):
        car = bot.info.my_car
        home = bot.info.own_goal
        target = home

        closest_enemy, enemy_dist = bot.info.closest_enemy(bot.info.ball.pos)

        car_to_home = home - car.pos
        dist = norm(car_to_home)
        vel_f_home = proj_onto_size(car.vel, car_to_home)

        if vel_f_home * 2 > dist:
            target = bot.info.ball.pos

        boost = 40 - (dist / 100) + enemy_dist / 200
        dodge = dist > 1500 or enemy_dist < dist

        return self.go_towards_point(bot, target, 2300, True, boost_min=boost, can_dodge=dodge)


class AimCone:
    def __init__(self, right_most, left_most):
        # Right angle and direction
        if isinstance(right_most, float):
            self.right_ang = fix_ang(right_most)
            self.right_dir = Vec3(math.cos(right_most), math.sin(right_most), 0)
        elif isinstance(right_most, Vec3):
            self.right_ang = math.atan2(right_most.y, right_most.x)
            self.right_dir = normalize(right_most)
        # Left angle and direction
        if isinstance(left_most, float):
            self.left_ang = fix_ang(left_most)
            self.left_dir = Vec3(math.cos(left_most), math.sin(left_most), 0)
        elif isinstance(left_most, Vec3):
            self.left_ang = math.atan2(left_most.y, left_most.x)
            self.left_dir = normalize(left_most)

    def contains_direction(self, direction, span_offset: float=0):
        ang_delta = angle_between(direction, self.get_center_dir())
        return abs(ang_delta) < self.span_size() / 2.0 + span_offset

    def span_size(self):
        if self.right_ang < self.left_ang:
            return math.tau + self.right_ang - self.left_ang
        else:
            return self.right_ang - self.left_ang

    def get_center_ang(self):
        return fix_ang(self.right_ang - self.span_size() / 2)

    def get_center_dir(self):
        ang = self.get_center_ang()
        return Vec3(math.cos(ang), math.sin(ang), 0)

    def get_closest_dir_in_cone(self, direction, span_offset: float=0):
        if self.contains_direction(direction, span_offset):
            return normalize(direction)
        else:
            ang_to_right = abs(angle_between(direction, self.right_dir))
            ang_to_left = abs(angle_between(direction, self.left_dir))
            return self.right_dir if ang_to_right < ang_to_left else self.left_dir

    def get_goto_point(self, bot, src, point):
        point = xy(point)
        desired_dir = self.get_center_dir()

        desired_dir_inv = -1 * desired_dir
        car_pos = xy(src)
        point_to_car = car_pos - point

        ang_to_desired_dir = angle_between(desired_dir_inv, point_to_car)

        ANG_ROUTE_ACCEPTED = math.pi / 4.3
        can_go_straight = abs(ang_to_desired_dir) < self.span_size() / 2.0
        can_with_route = abs(ang_to_desired_dir) < self.span_size() / 2.0 + ANG_ROUTE_ACCEPTED
        point = point + desired_dir_inv * 50
        if can_go_straight:
            return point, 1.0
        elif can_with_route:
            ang_to_right = abs(angle_between(point_to_car, -1 * self.right_dir))
            ang_to_left = abs(angle_between(point_to_car, -1 * self.left_dir))
            closest_dir = self.right_dir if ang_to_right < ang_to_left else self.left_dir

            goto = curve_from_arrival_dir(car_pos, point, closest_dir)

            goto.x = clip(goto.x, -Field.WIDTH / 2, Field.WIDTH / 2)
            goto.y = clip(goto.y, -Field.LENGTH / 2, Field.LENGTH / 2)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car_pos, goto, bot.renderer.create_color(255, 150, 150, 150))
                bot.renderer.draw_line_3d(point, goto, bot.renderer.create_color(255, 150, 150, 150))

                # Bezier
                rendering.draw_bezier(bot, [car_pos, goto, point])

            return goto, 0.5
        else:
            return None, 1

    def draw(self, bot, center, arm_len=500, arm_count=5, r=255, g=255, b=255):
        renderer = bot.renderer
        ang_step = self.span_size() / (arm_count - 1)

        for i in range(arm_count):
            ang = self.right_ang - ang_step * i
            arm_dir = Vec3(math.cos(ang), math.sin(ang), 0)
            end = center + arm_dir * arm_len
            alpha = 255 if i == 0 or i == arm_count - 1 else 110
            renderer.draw_line_3d(center, end, renderer.create_color(alpha, r, g, b))


class ShotController:
    def __init__(self):
        self.controls = SimpleControllerState()
        self.dodge = None
        self.last_point = None
        self.last_dodge_end_time = 0
        self.dodge_cooldown = 0.26
        self.recovery = None
        self.aim_is_ok = False
        self.waits_for_fall = False
        self.ball_is_flying = False
        self.can_shoot = False
        self.using_curve = False
        self.curve_point = None
        self.ball_when_hit = None

    def with_aiming(self, bot, aim_cone: AimCone, time: float, dodge_hit: bool=True):

        #       aim: |           |           |           |
        #  ball      |   bad     |    ok     |   good    |
        # z pos:     |           |           |           |
        # -----------+-----------+-----------+-----------+
        #  too high  |   give    |   give    |   wait/   |
        #            |    up     |    up     |  improve  |
        # -----------+ - - - - - + - - - - - + - - - - - +
        #   medium   |   give    |  improve  |  aerial   |
        #            |    up     |    aim    |           |
        # -----------+ - - - - - + - - - - - + - - - - - +
        #   soon on  |  improve  |  slow     |   small   |
        #   ground   |    aim    |  curve    |   jump    |
        # -----------+ - - - - - + - - - - - + - - - - - +
        #  on ground |  improve  |  fast     |  fast     |
        #            |   aim??   |  curve    |  straight |
        # -----------+ - - - - - + - - - - - + - - - - - +

        # FIXME if the ball is not on the ground we treat it as 'soon on ground' in all other cases

        self.controls = SimpleControllerState()
        self.aim_is_ok = False
        self.waits_for_fall = False
        self.ball_is_flying = False
        self.can_shoot = False
        self.using_curve = False
        self.curve_point = None
        self.ball_when_hit = None
        car = bot.info.my_car

        ball_soon = ball_predict(bot, time)
        car_to_ball_soon = ball_soon.pos - car.pos

        if ball_soon.pos.z < 110 or (ball_soon.pos.z < 475 and ball_soon.vel.z <= 0) or True: #FIXME Always true

            # The ball is on the ground or soon on the ground

            if 275 < ball_soon.pos.z < 475 and aim_cone.contains_direction(car_to_ball_soon):
                # Can we hit it if we make a small jump?
                vel_f = proj_onto_size(car.vel, xy(car_to_ball_soon))
                car_expected_pos = car.pos + car.vel * time
                ball_soon_flat = xy(ball_soon.pos)
                diff = norm(car_expected_pos - ball_soon_flat)

                if bot.do_rendering:
                    bot.renderer.draw_line_3d(car.pos, car_expected_pos, bot.renderer.lime())
                    bot.renderer.draw_rect_3d(car_expected_pos, 12, 12, True, bot.renderer.lime())

                if vel_f > 400:
                    if diff < 150:
                        bot.maneuver = SmallJumpManeuver(bot, lambda b: b.info.ball.pos)

            if 110 < ball_soon.pos.z: # and ball_soon.vel.z <= 0:
                # The ball is slightly in the air, lets wait just a bit more
                self.waits_for_fall = True
                ball_landing = next_ball_landing(bot, ball_soon, size=100)
                time = time + ball_landing.time
                ball_soon = ball_predict(bot, time)
                car_to_ball_soon = ball_soon.pos - car.pos

            self.ball_when_hit = ball_soon

            # The ball is on the ground, are we in position for a shot?
            if aim_cone.contains_direction(car_to_ball_soon):

                # Straight shot

                self.aim_is_ok = True
                self.can_shoot = True

                if norm(car_to_ball_soon) < 240 + Ball.RADIUS and aim_cone.contains_direction(car_to_ball_soon):
                    bot.drive.start_dodge(bot)

                offset_point = xy(ball_soon.pos) - 50 * aim_cone.get_center_dir()
                speed = self.determine_speed(norm(car_to_ball_soon), time)
                self.controls = bot.drive.go_towards_point(bot, offset_point, target_vel=speed, slide=True, boost_min=0, can_keep_speed=False)
                return self.controls

            elif aim_cone.contains_direction(car_to_ball_soon, math.pi / 5):

                # Curve shot

                self.aim_is_ok = True
                self.using_curve = True
                self.can_shoot = True

                offset_point = xy(ball_soon.pos) - 50 * aim_cone.get_center_dir()
                closest_dir = aim_cone.get_closest_dir_in_cone(car_to_ball_soon)
                self.curve_point = curve_from_arrival_dir(car.pos, offset_point, closest_dir)

                self.curve_point.x = clip(self.curve_point.x, -Field.WIDTH / 2, Field.WIDTH / 2)
                self.curve_point.y = clip(self.curve_point.y, -Field.LENGTH / 2, Field.LENGTH / 2)

                if dodge_hit and norm(car_to_ball_soon) < 240 + Ball.RADIUS and angle_between(car.forward, car_to_ball_soon) < 0.5 and aim_cone.contains_direction(car_to_ball_soon):
                    bot.drive.start_dodge(bot)

                speed = self.determine_speed(norm(car_to_ball_soon), time)
                self.controls = bot.drive.go_towards_point(bot, self.curve_point, target_vel=speed, slide=True, boost_min=0, can_keep_speed=False)
                return self.controls

            else:

                # We are NOT in position!
                self.aim_is_ok = False

                pass

        else:

            if aim_cone.contains_direction(car_to_ball_soon):
                self.waits_for_fall = True
                self.aim_is_ok = True
                #self.can_shoot = False
                pass  # Allow small aerial (wait if ball is too high)

            elif aim_cone.contains_direction(car_to_ball_soon, math.pi / 4):
                self.ball_is_flying = True
                pass  # Aim is ok, but ball is in the air

    def determine_speed(self, dist, time):
        if time == 0:
            return 2300
        elif dist < 1700:
            return dist / time
        else:
            extra = (dist - 1700) / 1000
            return (1 + extra) * dist / time


def celebrate(bot):
    controls = SimpleControllerState()
    controls.steer = math.sin(time.time() * 10)
    controls.throttle = -1
    return controls


# ----------------------------------------- Helper functions --------------------------------


def is_heading_towards(ang, dist):
    # The further away the car is the less accurate the angle is required
    required_ang = 0.05 + 0.0001 * dist
    return abs(ang) <= required_ang


def turn_radius(vf):
    if vf == 0:
        return 0
    return 1.0 / turn_curvature(vf)


def turn_curvature(vf):
    if 0.0 <= vf < 500.0:
        return 0.006900 - 5.84e-6 * vf
    elif 500.0 <= vf < 1000.0:
        return 0.005610 - 3.26e-6 * vf
    elif 1000.0 <= vf < 1500.0:
        return 0.004300 - 1.95e-6 * vf
    elif 1500.0 <= vf < 1750.0:
        return 0.003025 - 1.10e-6 * vf
    elif 1750.0 <= vf < 2500.0:
        return 0.001800 - 0.40e-6 * vf
    else:
        return 0.0
