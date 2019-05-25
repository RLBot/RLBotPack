from RLUtilities.Simulation import Car, Input

import predict
import render
from moves import AimCone
from plans import DodgePlan
from rlmath import *


class Carry:
    def __init__(self):
        self.is_dribbling = False
        self.flick_timer = 0

        # Constants
        self.extra_utility_bias = 0.2
        self.wait_before_flick = 0.26
        self.flick_init_jump_duration = 0.07
        self.required_distance_to_ball_for_flick = 173
        self.offset_bias = 36

    def utility(self, bot):
        car = bot.info.my_car
        ball = bot.info.ball

        car_to_ball = car.pos - ball.pos

        bouncing_b = ball.pos[Z] > 130 or abs(ball.vel[Z]) > 300
        if not bouncing_b:
            return 0

        dist_01 = clip01(1 - norm(car_to_ball) / 3000)

        head_dir = lerp(vec3(0, 0, 1), car.forward(), 0.1)
        ang = angle_between(head_dir, car_to_ball)
        ang_01 = clip01(1 - ang / (math.pi / 2))

        return clip01(0.6 * ang_01
                              + 0.4 * dist_01
                              #  - 0.3 * bot.analyzer.team_mate_has_ball_01
                              + self.is_dribbling * self.extra_utility_bias)

    def execute(self, bot):
        self.is_dribbling = True

        car = bot.info.my_car
        ball = bot.info.ball
        ball_landing = predict.next_ball_landing(bot)
        ball_to_goal = bot.info.enemy_goal - ball.pos

        # Decide on target pos and speed
        target = ball_landing.data["obj"].pos - self.offset_bias * normalize(ball_to_goal)
        dist = norm(target - bot.info.my_car.pos)
        speed = 1400 if ball_landing.time == 0 else dist / ball_landing.time

        # Do a flick?
        car_to_ball = ball.pos - car.pos
        dist = norm(car_to_ball)
        if dist <= self.required_distance_to_ball_for_flick:
            self.flick_timer += 0.016666
            if self.flick_timer > self.wait_before_flick:
                bot.plan = DodgePlan(bot.info.enemy_goal)  # use flick_init_jump_duration?
        else:
            self.flick_timer = 0

            # dodge on far distances
            if dist > 2450 and speed > 1410:
                ctt_n = normalize(target - car.pos)
                vtt = dot(bot.info.my_car.vel, ctt_n) / dot(ctt_n, ctt_n)
                if vtt > 750:
                    bot.plan = DodgePlan(target)

        controls = bot.drive.go_towards_point(bot, target, target_vel=speed, slide=False, boost=False, can_keep_speed=False, can_dodge=True, wall_offset_allowed=0)
        bot.controls = controls

        if bot.do_rendering:
            bot.renderer.draw_line_3d(car.pos, target, bot.renderer.pink())

    def reset(self):
        self.is_dribbling = False
        self.flick_timer = 0


class ShootAtGoal:
    def __init__(self):
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility(self, bot):
        ball_soon = predict.ball_predict(bot, 1)

        arena_length2 = bot.info.team_sign * FIELD_LENGTH / 2
        own_half_01 = clip01(remap(arena_length2, -arena_length2, 0.0, 1.1, ball_soon.pos[Y]))

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        self.ball_to_goal_right = bot.info.enemy_goal_right - reachable_ball.pos
        self.ball_to_goal_left = bot.info.enemy_goal_left - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_right, self.ball_to_goal_left)
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball)

        return clip01(own_half_01 + 0.1 * in_position)

    def execute(self, bot):

        car = bot.info.my_car
        ball = bot.info.ball

        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, predict.time_till_reach_ball(car, ball))
        if bot.do_rendering:
            self.aim_cone.draw(bot, bot.shoot.ball_when_hit.pos, b=0)

        hit_pos = bot.shoot.ball_when_hit.pos
        dist = norm(car.pos - hit_pos)
        closest_enemy, enemy_dist = bot.info.closest_enemy(0.5 * (hit_pos + ball.pos))

        if not bot.shoot.can_shoot and is_closer_to_goal_than(car.pos, hit_pos, bot.info.team):
            # Can't shoot but or at least on the right side: Chase

            goal_to_ball = normalize(hit_pos - bot.info.enemy_goal)
            offset_ball = hit_pos + goal_to_ball * BALL_RADIUS * 0.9
            bot.controls = bot.drive.go_towards_point(bot, offset_ball, target_vel=2200, slide=False, boost=True)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, offset_ball, bot.renderer.yellow())

        elif not bot.shoot.aim_is_ok and hit_pos[Y] * -bot.info.team_sign > 4350 and abs(hit_pos[X]) > 900 and not dist < 450:
            # hit_pos is an enemy corner and we are not close: Avoid enemy corners and just wait

            enemy_to_ball = normalize(hit_pos - closest_enemy.pos)
            wait_point = hit_pos + enemy_to_ball * enemy_dist  # a point 50% closer to the center of the field
            wait_point = lerp(wait_point, ball.pos + vec3(0, bot.info.team_sign * 3000, 0), 0.5)
            bot.controls = bot.drive.go_towards_point(bot, wait_point, norm(car.pos - wait_point), slide=False, boost=False, can_keep_speed=True, can_dodge=False)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, wait_point, bot.renderer.yellow())

        elif not bot.shoot.can_shoot:
            # return home
            bot.controls = bot.drive.go_home(bot)

        else:
            # Shoot !
            bot.controls = shoot_controls

            if bot.shoot.using_curve and bot.do_rendering:
                render.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])


class ClearBall:
    def __init__(self, bot):
        if bot.team == 0:
            # blue
            self.aim_cone = AimCone(.8 * math.pi, .2 * math.pi)
        else:
            # orange
            self.aim_cone = AimCone(-.1 * math.pi, -.9 * math.pi)

    def utility(self, bot):
        team_sign = bot.info.team_sign

        length = team_sign * FIELD_LENGTH / 2
        ball_own_half_01 = clip01(remap(-length, length, -0.2, 1.2, bot.info.ball.pos[Y]))

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball, math.pi / 8)

        return ball_own_half_01 * in_position

    def execute(self, bot):
        car = bot.info.my_car
        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        hit_pos = bot.shoot.ball_when_hit.pos

        if bot.do_rendering:
            self.aim_cone.draw(bot, hit_pos, r=0, g=170, b=255)

        if bot.shoot.can_shoot:
            bot.controls = shoot_controls

            if bot.shoot.using_curve and bot.do_rendering:
                render.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])

        else:
            # go home-ish
            own_goal = lerp(bot.info.own_goal, bot.info.ball.pos, 0.5)
            bot.controls = bot.drive.go_towards_point(bot, own_goal, target_vel=1460, slide=True, boost=True, can_keep_speed=True)


class SaveGoal:
    def __init__(self, bot):
        team_sign = bot.info.team_sign
        self.own_goal_right = vec3(-820 * team_sign, 5120 * team_sign, 0)
        self.own_goal_left = vec3(820 * team_sign, 5120 * team_sign, 0)
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility(self, bot):
        team_sign = bot.info.team_sign
        ball = bot.info.ball

        ball_to_goal = bot.info.own_goal - ball.pos
        too_close = norm(ball_to_goal) < GOAL_WIDTH / 2 + BALL_RADIUS

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        hits_goal = hits_goal_prediction.happens and sign(ball.vel[Y]) == team_sign and hits_goal_prediction.time < 3

        return hits_goal or too_close

    def execute(self, bot):

        car = bot.info.my_car
        ball = bot.info.ball

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        reach_time = clip(predict.time_till_reach_ball(car, ball), 0, hits_goal_prediction.time - 0.5)
        reachable_ball = predict.ball_predict(bot, reach_time)
        self.ball_to_goal_right = self.own_goal_right - reachable_ball.pos
        self.ball_to_goal_left = self.own_goal_left - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_left, self.ball_to_goal_right)

        self.aim_cone.draw(bot, reachable_ball.pos, r=200, g=0, b=160)

        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, reach_time)

        if not bot.shoot.can_shoot:
            # Go home
            bot.controls = bot.drive.go_home(bot)
        else:
            bot.controls = shoot_controls
