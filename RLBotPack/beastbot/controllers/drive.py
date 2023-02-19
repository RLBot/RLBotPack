import math

from rlbot.agents.base_agent import SimpleControllerState

from controllers.other import turn_radius, is_heading_towards
from maneuvers.dodge import DodgeManeuver
from maneuvers.halfflip import HalfFlipManeuver
from maneuvers.recovery import RecoveryManeuver
from utility import rendering
from utility.info import is_near_wall, Field
from utility.rlmath import lerp, sign, clip
from utility.vec import Vec3, angle_between, xy, dot, norm, proj_onto_size, normalize


class HandbrakeLimiter:
    def __init__(self):
        self.tick = 0
        self.HANDBRAKE_FRAMES = 10
        self.WAIT_FRAMES = 16

    def can_handbrake(self):
        self.tick = (self.tick % (self.HANDBRAKE_FRAMES + self.WAIT_FRAMES))
        return self.tick >= self.WAIT_FRAMES


class DriveController:
    def __init__(self):
        self.controls = SimpleControllerState()
        self.dodge = None
        self.last_point = None
        self.last_dodge_end_time = 0
        self.dodge_cooldown = 0.27
        self.recovery = None
        self.handbrake_limiter = HandbrakeLimiter()

    def start_dodge(self, bot):
        if self.dodge is None:
            self.dodge = DodgeManeuver(bot, self.last_point)

    def go_towards_point(self, bot, point: Vec3, target_vel=1430, slide=False, boost_min=101, can_keep_speed=True, can_dodge=True, wall_offset_allowed=125) -> SimpleControllerState:
        REQUIRED_ANG_FOR_SLIDE = 1.65
        REQUIRED_VELF_FOR_DODGE = 1100

        car = bot.info.my_car

        # Dodge is done
        if self.dodge is not None and self.dodge.done:
            self.dodge = None
            self.last_dodge_end_time = bot.info.time
        # Continue dodge
        elif self.dodge is not None:
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
                and dist > vel_towards_point + 500 + 900 and bot.info.time > self.last_dodge_end_time + self.dodge_cooldown:
            self.dodge = DodgeManeuver(bot, point)
        # Start half-flip
        elif can_dodge and abs(angle) >= 3 and vel_towards_point < 50\
                and dist > -vel_towards_point + 500 + 900 and bot.info.time > self.last_dodge_end_time + self.dodge_cooldown:
            self.dodge = HalfFlipManeuver(bot, boost=car.boost > boost_min + 10)

        # Is point right behind? Maybe reverse instead
        if -100 < point_local.x < 0 and abs(point_local.y) < 50:
            #bot.print("Reversing?")
            pass

        # Is in turn radius deadzone?
        tr = turn_radius(abs(vel_f + 50))  # small bias
        tr_side = sign(angle)
        tr_center_local = Vec3(0, tr * tr_side, 10)
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
            if point_local.x < 110 and point_local.y < 400 and norm(car.vel) < 300:
                # Brake or go backwards when the point is really close but not in front of us
                self.controls.throttle = clip(-0.25 + point_local.x / -110.0, 0, -1)
                self.controls.steer = -0.5 * sign(angle)

        else:
            # Should drop speed or just keep up the speed?
            if can_keep_speed and target_vel < vel_towards_point:
                target_vel = vel_towards_point
            else:
                # Small lerp adjustment
                target_vel = lerp(vel_towards_point, target_vel, 1.1)

            # Turn and maybe slide
            self.controls.steer = clip(angle + (2.5*angle) ** 3, -1.0, 1.0)
            if slide and abs(angle) > REQUIRED_ANG_FOR_SLIDE and self.handbrake_limiter.can_handbrake():
                self.controls.handbrake = True
                self.controls.steer = sign(angle)
            else:
                self.controls.handbrake = False

            # Overshoot target vel for quick adjustment
            target_vel = lerp(vel_towards_point, target_vel, 1.2)

            # Find appropriate throttle/boost
            if vel_towards_point < target_vel:
                self.controls.throttle = 1
                if boost_min < car.boost and vel_towards_point + 80 < target_vel and target_vel > 1400 \
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

        car_to_ball = bot.info.ball.pos - car.pos
        facing_ball = dot(car.forward, normalize(car_to_ball))

        # if vel_f_home * 2 > dist:
        #     target = bot.info.ball.pos

        if dist < 300 and facing_ball > 0.5:
            return SimpleControllerState()

        boost = 40 - (dist / 100) + enemy_dist / 200
        dodge = dist > 1500 or enemy_dist < dist

        return self.go_towards_point(bot, target, 2300, True, boost_min=boost, can_dodge=dodge)
