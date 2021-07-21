import math

from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from maneuvers.jump_shot import JumpShotManeuver
from utility.curves import curve_from_arrival_dir
from utility.info import Field, Ball
from utility.predict import ball_predict, next_ball_landing
from utility.rlmath import clip
from utility.vec import angle_between, xy, dot, norm, proj_onto_size, normalize, Vec3, axis_to_rotation


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
        #   > 1200   |    up     |    up     |  improve  |
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
        car = bot.info.my_car

        ball_soon = ball_predict(bot, time)
        car_to_ball_soon = ball_soon.pos - car.pos
        dot_facing_score = dot(normalize(car_to_ball_soon), normalize(car.forward))
        dot_facing_score_2d = dot(normalize(xy(car_to_ball_soon)), normalize(xy(car.forward)))
        vel_towards_ball_soon = proj_onto_size(car.vel, car_to_ball_soon)
        is_facing = 0.1 < dot_facing_score
        is_facing_2d = 0.3 < dot_facing_score

        self.ball_when_hit = ball_soon

        if ball_soon.pos.z < 110:

            # The ball is on the ground

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

                if norm(car_to_ball_soon) < 400 + Ball.RADIUS and aim_cone.contains_direction(car_to_ball_soon)\
                        and vel_towards_ball_soon > 300:
                    bot.drive.start_dodge(bot, towards_ball=True)

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

                if dodge_hit and norm(car_to_ball_soon) < 400 + Ball.RADIUS and angle_between(car.forward, car_to_ball_soon) < 0.5\
                        and aim_cone.contains_direction(car_to_ball_soon) and vel_towards_ball_soon > 300:
                    bot.drive.start_dodge(bot, towards_ball=True)

                speed = self._determine_speed(norm(car_to_ball_soon), time)
                self.controls = bot.drive.towards_point(bot, self.curve_point, target_vel=speed, slide=True, boost_min=0, can_keep_speed=False)
                return self.controls

            else:

                # We are NOT in position!
                return None

        elif ball_soon.pos.z < 600 and ball_soon.vel.z <= 0:

            # Ball is on ground soon. Is it worth waiting? TODO if aim is bad, do a slow curve - or delete case?
            pass

        # ---------------------------------------
        # Ball is in the air, or going in the air

        if 200 < ball_soon.pos.z < 1400 and aim_cone.contains_direction(car_to_ball_soon) and is_facing_2d:

            # Can we hit it if we make jump shot or aerial shot?

            vel_f = proj_onto_size(car.vel, xy(car_to_ball_soon))
            aerial = ball_soon.pos.z > 750

            if vel_f > 400:  # Some forward momentum is required

                flat_dist = norm(xy(car_to_ball_soon))
                # This range should be good https://www.desmos.com/calculator/bx9imtiqi5
                good_height = 0.3 * ball_soon.pos.z < flat_dist < 4 * ball_soon.pos.z

                if good_height:

                    # Alternative ball positions
                    alternatives = [
                        (ball_predict(bot, time * 0.8), time * 0.8),
                        (ball_predict(bot, time * 0.9), time * 0.9),
                        (ball_soon, time),
                        (ball_predict(bot, time * 1.1), time * 1.1),
                        (ball_predict(bot, time * 1.2), time * 1.2)
                    ]

                    for alt_ball, alt_time in alternatives:

                        potential_small_jump_shot = JumpShotManeuver(bot, alt_ball.pos, bot.info.time + alt_time, do_second_jump=aerial)
                        jump_shot_viable = potential_small_jump_shot.is_viable(car, bot.info.time)

                        if jump_shot_viable:
                            self.can_shoot = True
                            self.aim_is_ok = True
                            bot.maneuver = potential_small_jump_shot
                            return bot.maneuver.exec(bot)

        self.ball_is_flying = True
        return self.controls

    def towards(self, bot, target: Vec3, time: float, allowed_uncertainty: float = 0.3, dodge_hit: bool = True):

        ball_soon = ball_predict(bot, time)
        ball_soon_to_target_dir = normalize(target - ball_soon.pos)
        right = dot(axis_to_rotation(Vec3(z=allowed_uncertainty)), ball_soon_to_target_dir)
        left = dot(axis_to_rotation(Vec3(z=-allowed_uncertainty)), ball_soon_to_target_dir)
        aim_cone = AimCone(right, left)

        aim_cone.draw(ball_soon.pos, r=0, g=0)

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
