import math

from rlbot.agents.base_agent import SimpleControllerState

from controllers.other import turn_radius, is_heading_towards
from maneuvers.dodge import DodgeManeuver
from maneuvers.halfflip import HalfFlipManeuver
from maneuvers.recovery import RecoveryManeuver
from utility import rendering
from utility.info import Field, is_near_wall, Goal
from utility.rlmath import lerp, sign, clip
from utility.vec import Vec3, angle_between, xy, dot, norm, proj_onto_size, normalize


class DriveController:
    def __init__(self):
        self.controls = SimpleControllerState()
        self.dodge = None
        self.last_point = None
        self.last_dodge_end_time = 0
        self.dodge_cooldown = 0.27
        self.recovery = None

    def start_dodge(self, bot, towards_ball: bool = False):
        if self.dodge is None:
            if towards_ball:
                self.dodge = DodgeManeuver(bot, lambda b: b.info.ball.pos)
            else:
                self.dodge = DodgeManeuver(bot, self.last_point)

    def towards_point(self, bot, point: Vec3, target_vel=1430, slide=False, boost_min=101, can_keep_speed=True, can_dodge=True, wall_offset_allowed=125) -> SimpleControllerState:
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
            bot.maneuver = RecoveryManeuver()
            return self.controls

        # Get down from wall by choosing a point close to ground
        if not is_near_wall(point, wall_offset_allowed) and angle_between(car.up, Vec3(0, 0, 1)) > math.pi * 0.31:
            point = lerp(xy(car.pos), xy(point), 0.5)

        # If the car is in a goal, avoid goal posts
        self._avoid_goal_post(bot, point)

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
        elif can_dodge and abs(angle) >= 3 and vel_towards_point < 0\
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
        if car.on_ground and bot.do_rendering and False:
            tr_center_world = car.pos + dot(car.rot, tr_center_local)
            tr_center_world_2 = car.pos + dot(car.rot, -1 * tr_center_local)
            color = bot.renderer.orange()
            rendering.draw_circle(bot, tr_center_world, car.up, tr, 22, color)
            rendering.draw_circle(bot, tr_center_world_2, car.up, tr, 22, color)

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

    @staticmethod
    def _avoid_goal_post(bot, point):
        car = bot.info.my_car
        car_to_point = point - car.pos

        # Car is not in goal, not adjustment needed
        if abs(car.pos.y) < Field.LENGTH / 2:
            return

        # Car can go straight, not adjustment needed
        if car_to_point.x == 0:
            return

        # Do we need to cross a goal post to get to the point?
        goalx = Goal.WIDTH2 - 100
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

    def stay_at(self, bot, point: Vec3, looking_at: Vec3):

        OKAY_DIST = 100

        car = bot.info.my_car
        car_to_point = point - car.pos
        car_to_point_dir = normalize(point - car.pos)
        dist = norm(car_to_point)

        if dist > OKAY_DIST:
            return self.towards_point(bot, point, int(dist * 2))
        else:
            look_dir = normalize(looking_at - car.pos)
            facing_correctly = dot(car.forward, look_dir) > 0.9
            if facing_correctly:
                return SimpleControllerState()
            else:
                ctrls = SimpleControllerState()
                ctrls.throttle = 0.7 * sign(dot(car.forward, car_to_point_dir))
                ctrls.steer = -ctrls.throttle * sign(dot(car.left, car_to_point_dir))

                return ctrls

    def home(self, bot):

        return self.stay_at(bot, bot.info.own_goal.pos, bot.info.ball.pos)
