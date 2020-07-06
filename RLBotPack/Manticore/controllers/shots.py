import math

from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from maneuvers.small_jump import SmallJumpManeuver
from util.curves import curve_from_arrival_dir
from util.info import Field, Ball
from util.predict import ball_predict, next_ball_landing
from util.rlmath import clip
from util.vec import angle_between, xy, dot, norm, proj_onto_size, normalize, Vec3, axis_to_rotation


class ShotController:
    def __init__(self):
        self.controls = SimpleControllerState()
        self.recovery = None
        self.aim_is_ok = False
        self.waits_for_fall = False
        self.ball_is_flying = False
        self.can_shoot = False
        self.using_curve = False
        self.curve_point = None
        self.ball_when_hit = None

    def with_aiming(self, bot, aim_cone: AimCone, time: float, dodge_hit: bool = True):

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
        dot_facing_score = dot(normalize(car_to_ball_soon), normalize(car.forward))
        vel_towards_ball_soon = proj_onto_size(car.vel, car_to_ball_soon)
        is_facing = 0 < dot_facing_score

        if ball_soon.pos.z < 110 or (ball_soon.pos.z < 475 and ball_soon.vel.z <= 0) or True: #FIXME Always true

            # The ball is on the ground or soon on the ground

            if 275 < ball_soon.pos.z < 475 and aim_cone.contains_direction(car_to_ball_soon):
                # Can we hit it if we make a small jump?
                vel_f = proj_onto_size(car.vel, xy(car_to_ball_soon))
                car_expected_pos = car.pos + car.vel * time
                ball_soon_flat = xy(ball_soon.pos)
                diff = norm(car_expected_pos - ball_soon_flat)
                ball_in_front = dot(ball_soon.pos - car_expected_pos, car.vel) > 0

                if bot.do_rendering:
                    bot.renderer.draw_line_3d(car.pos, car_expected_pos, bot.renderer.lime())
                    bot.renderer.draw_rect_3d(car_expected_pos, 12, 12, True, bot.renderer.lime())

                if vel_f > 400:
                    if diff < 150 and ball_in_front:
                        bot.maneuver = SmallJumpManeuver(bot, lambda b: b.info.ball.pos)

            if 110 < ball_soon.pos.z:  # and ball_soon.vel.z <= 0:
                # The ball is slightly in the air, lets wait just a bit more
                self.waits_for_fall = True
                ball_landing = next_ball_landing(bot, ball_soon, size=100)
                time = time + ball_landing.time
                ball_soon = ball_predict(bot, time)
                car_to_ball_soon = ball_soon.pos - car.pos

            self.ball_when_hit = ball_soon

            # The ball is on the ground, are we in position for a shot?
            if aim_cone.contains_direction(car_to_ball_soon) and is_facing:

                # Straight shot

                self.aim_is_ok = True
                self.can_shoot = True

                if norm(car_to_ball_soon) < 240 + Ball.RADIUS and aim_cone.contains_direction(car_to_ball_soon)\
                        and vel_towards_ball_soon > 300:
                    bot.drive.start_dodge(bot)

                offset_point = xy(ball_soon.pos) - 50 * aim_cone.get_center_dir()
                speed = self._determine_speed(norm(car_to_ball_soon), time)
                self.controls = bot.drive.towards_point(bot, offset_point, target_vel=speed, slide=True, boost_min=0, can_keep_speed=False)
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

                if dodge_hit and norm(car_to_ball_soon) < 240 + Ball.RADIUS and angle_between(car.forward, car_to_ball_soon) < 0.5\
                        and aim_cone.contains_direction(car_to_ball_soon) and vel_towards_ball_soon > 300:
                    bot.drive.start_dodge(bot)

                speed = self._determine_speed(norm(car_to_ball_soon), time)
                self.controls = bot.drive.towards_point(bot, self.curve_point, target_vel=speed, slide=True, boost_min=0, can_keep_speed=False)
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

    def towards(self, bot, target: Vec3, time: float, allowed_uncertainty: float = 0.3, dodge_hit: bool = True):

        ball_soon = ball_predict(bot, time)
        ball_soon_to_target_dir = normalize(target - ball_soon.pos)
        right = dot(axis_to_rotation(Vec3(z=allowed_uncertainty)), ball_soon_to_target_dir)
        left = dot(axis_to_rotation(Vec3(z=-allowed_uncertainty)), ball_soon_to_target_dir)
        aim_cone = AimCone(right, left)

        aim_cone.draw(bot, ball_soon.pos, r=0, g=0)

        return self.with_aiming(bot, aim_cone, time, dodge_hit)

    def any_touch(self, bot, time: float, dodge_hit: bool = True):

        ball_soon = ball_predict(bot, time)
        car_to_ball = ball_soon.pos - bot.info.my_car.pos

        return self.towards(bot, ball_soon.pos + car_to_ball, time, dodge_hit) or SimpleControllerState()


    @staticmethod
    def _determine_speed(dist, time):
        if time == 0:
            return 2300
        elif dist < 1700:
            return dist / time
        else:
            extra = (dist - 1700) / 1000
            return (1 + extra) * dist / time
