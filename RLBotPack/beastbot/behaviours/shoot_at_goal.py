from rlbot.agents.base_agent import SimpleControllerState

from behaviours.moves import AimCone
from behaviours.utsystem import Choice
from maneuvers.collect_boost import CollectClosestBoostManeuver, filter_pads
from utility import predict, rendering
from utility.info import Field, Ball
from utility.rlmath import clip01, remap, is_closer_to_goal_than, lerp
from utility.vec import norm, normalize, Vec3, xy, dot


class ShootAtGoal(Choice):
    def __init__(self):
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None
        self.temp_utility_desire_boost = 0

    def utility(self, bot) -> float:

        if self.temp_utility_desire_boost > 0:
            self.temp_utility_desire_boost = max(0, self.temp_utility_desire_boost - bot.info.dt)
        elif self.temp_utility_desire_boost < 0:
            self.temp_utility_desire_boost = min(0, self.temp_utility_desire_boost + bot.info.dt)

        ball_soon = predict.ball_predict(bot, 1)

        arena_length2 = bot.info.team_sign * Field.LENGTH / 2
        own_half_01 = clip01(remap(arena_length2, -arena_length2, 0.0, 1.1, ball_soon.pos.y))

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        self.ball_to_goal_right = bot.info.enemy_goal_right - reachable_ball.pos
        self.ball_to_goal_left = bot.info.enemy_goal_left - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_right, self.ball_to_goal_left)
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball)

        # Chase ball right after kickoff. High right after kickoff
        kickoff_bias01 = max(0, 1 - bot.info.time_since_last_kickoff * 0.3)

        return clip01(own_half_01 + 0.1 * in_position + self.temp_utility_desire_boost + kickoff_bias01)

    def exec(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball

        my_hit_time = predict.time_till_reach_ball(car, ball)
        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, my_hit_time)
        if bot.do_rendering:
            self.aim_cone.draw(bot, bot.shoot.ball_when_hit.pos, b=0)

        hit_pos = bot.shoot.ball_when_hit.pos
        dist = norm(car.pos - hit_pos)
        closest_enemy, enemy_dist = bot.info.closest_enemy(0.5 * (hit_pos + ball.pos))

        if not bot.shoot.can_shoot and is_closer_to_goal_than(car.pos, hit_pos, bot.info.team):
            # Can't shoot but or at least on the right side: Chase

            goal_to_ball = normalize(hit_pos - bot.info.enemy_goal)
            offset_ball = hit_pos + goal_to_ball * Ball.RADIUS * 0.9
            enemy_hit_time = predict.time_till_reach_ball(closest_enemy, ball)
            enemy_hit_pos = predict.ball_predict(bot, enemy_hit_time).pos
            if enemy_hit_time < 1.5 * my_hit_time:
                self.temp_utility_desire_boost -= bot.info.dt
                if bot.do_rendering:
                    bot.renderer.draw_line_3d(closest_enemy.pos, enemy_hit_pos, bot.renderer.red())
                return bot.drive.go_home(bot)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, offset_ball, bot.renderer.yellow())

            return bot.drive.go_towards_point(bot, offset_ball, target_vel=2200, slide=False, boost_min=0)

        elif not bot.shoot.aim_is_ok and hit_pos.y * -bot.info.team_sign > 4250 and abs(hit_pos.x) > 900 and not dist < 420:
            # hit_pos is an enemy corner and we are not close: Avoid enemy corners and just wait

            enemy_to_ball = normalize(hit_pos - closest_enemy.pos)
            wait_point = hit_pos + enemy_to_ball * enemy_dist  # a point 50% closer to the center of the field
            wait_point = lerp(wait_point, ball.pos + Vec3(0, bot.info.team_sign * 3000, 0), 0.5)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, wait_point, bot.renderer.yellow())

            return bot.drive.go_towards_point(bot, wait_point, norm(car.pos - wait_point), slide=False, can_keep_speed=True, can_dodge=False)

        elif not bot.shoot.can_shoot:

            enemy_to_ball = normalize(xy(ball.pos - closest_enemy.pos))
            ball_to_my_goal = normalize(xy(bot.info.own_goal - ball.pos))
            dot_threat = dot(enemy_to_ball, ball_to_my_goal)  # 1 = enemy is in position, -1 = enemy is NOT in position

            if car.boost == 0 and ball.pos.y * bot.info.team_sign < 500 and dot_threat < 0.1:

                collect_center = ball.pos.y * bot.info.team_sign <= 0
                collect_small = closest_enemy.pos.y * bot.info.team_sign <= 0 or enemy_dist < 900
                pads = filter_pads(bot, bot.info.big_boost_pads, big_only=not collect_small, enemy_side=False, center=collect_center)
                bot.maneuver = CollectClosestBoostManeuver(bot, pads)
            # return home
            return bot.drive.go_home(bot)

        else:
            # Shoot !
            if bot.shoot.using_curve and bot.do_rendering:
                rendering.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])
            return shoot_controls
