from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from maneuvers.collect_boost import CollectClosestBoostManeuver, filter_pads
from strategy.objective import Objective
from strategy.utility_system import UtilityState
from utility import predict, rendering
from utility.info import Field, Ball
from utility.rlmath import clip01, remap, is_closer_to_goal_than, lerp
from utility.vec import norm, normalize, Vec3, xy, dot


class ShootAtGoal(UtilityState):
    def __init__(self):
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None
        self.temp_utility_desire_boost = 0

    def utility_score(self, bot) -> float:

        if self.temp_utility_desire_boost > 0:
            self.temp_utility_desire_boost = max(0, self.temp_utility_desire_boost - bot.info.dt)
        elif self.temp_utility_desire_boost < 0:
            self.temp_utility_desire_boost = min(0, self.temp_utility_desire_boost + bot.info.dt)

        car = bot.info.my_car
        ball_soon = predict.ball_predict(bot, 1)

        arena_length2 = bot.info.team_sign * Field.LENGTH2
        own_half_01 = clip01(remap(arena_length2, -arena_length2, 0.0, 1.1, ball_soon.pos.y))
        close_to_ball01 = clip01(1.0 - norm(car.pos - ball_soon.pos) / 3500) ** 0.5

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        self.ball_to_goal_right = bot.info.opp_goal.right_post - reachable_ball.pos
        self.ball_to_goal_left = bot.info.opp_goal.left_post - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_right, self.ball_to_goal_left)
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball)

        # Chase ball right after kickoff. High right after kickoff
        kickoff_bias01 = max(0, 1 - bot.info.time_since_last_kickoff * 0.3) * float(bot.info.my_car.objective == Objective.UNKNOWN)

        obj_bonus = {
            Objective.UNKNOWN: 1,
            Objective.GO_FOR_IT: 1,
            Objective.FOLLOW_UP: 0,
            Objective.ROTATING: 0,
            Objective.SOLO: 1,
        }[bot.info.my_car.objective]

        return clip01(close_to_ball01 * own_half_01 + 0.2 * in_position + self.temp_utility_desire_boost + kickoff_bias01) * obj_bonus

    def run(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball

        my_hit_time = predict.time_till_reach_ball(car, ball)
        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, my_hit_time)

        hit_pos = bot.shoot.ball_when_hit.pos
        dist = norm(car.pos - hit_pos)
        closest_enemy, enemy_dist = bot.info.closest_enemy(0.5 * (hit_pos + ball.pos))

        if not bot.shoot.can_shoot and is_closer_to_goal_than(car.pos, hit_pos, bot.info.team):
            # Can't shoot but or at least on the right side: Chase

            goal_to_ball = normalize(hit_pos - bot.info.opp_goal.pos)
            offset_ball = hit_pos + goal_to_ball * Ball.RADIUS * 0.9
            enemy_hit_time = predict.time_till_reach_ball(closest_enemy, ball)
            enemy_hit_pos = predict.ball_predict(bot, enemy_hit_time).pos
            if enemy_hit_time < 1.5 * my_hit_time:
                self.temp_utility_desire_boost -= bot.info.dt
                if bot.do_rendering:
                    bot.renderer.draw_line_3d(closest_enemy.pos, enemy_hit_pos, bot.renderer.red())
                return bot.drive.home(bot)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, offset_ball, bot.renderer.yellow())

            return bot.drive.towards_point(bot, offset_ball, target_vel=2200, slide=False, boost_min=0)

        elif len(bot.info.teammates) == 0 and not bot.shoot.aim_is_ok and hit_pos.y * -bot.info.team_sign > 4250 and abs(hit_pos.x) > 900 and not dist < 420:
            # hit_pos is an enemy corner and we are not close: Avoid enemy corners in 1s and just wait

            enemy_to_ball = normalize(hit_pos - closest_enemy.pos)
            wait_point = hit_pos + enemy_to_ball * enemy_dist  # a point 50% closer to the center of the field
            wait_point = lerp(wait_point, ball.pos + Vec3(0, bot.info.team_sign * 3000, 0), 0.5)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, wait_point, bot.renderer.yellow())

            return bot.drive.towards_point(bot, wait_point, norm(car.pos - wait_point), slide=False, can_keep_speed=True, can_dodge=False)

        elif bot.shoot.can_shoot:

            # Shoot !
            if bot.do_rendering:
                self.aim_cone.draw(bot, bot.shoot.ball_when_hit.pos, r=0, b=0)
                if bot.shoot.using_curve:
                    rendering.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])
            return shoot_controls

        else:
            # We can't shoot at goal reliably
            # How about a shot to the corners then?
            corners = [
                Vec3(-Field.WIDTH2, -bot.info.team_sign * Field.LENGTH2, 0),
                Vec3(Field.WIDTH2, -bot.info.team_sign * Field.LENGTH2, 0),
            ]
            for corner in corners:
                ctrls = bot.shoot.towards(bot, corner, bot.info.my_car.reach_ball_time)
                if bot.shoot.can_shoot:
                    self.aim_cone.draw(bot, bot.shoot.ball_when_hit.pos, b=0)
                    if bot.shoot.using_curve:
                        rendering.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])
                    return ctrls

            enemy_to_ball = normalize(xy(ball.pos - closest_enemy.pos))
            ball_to_my_goal = normalize(xy(bot.info.own_goal.pos - ball.pos))
            dot_threat = dot(enemy_to_ball, ball_to_my_goal)  # 1 = enemy is in position, -1 = enemy is NOT in position

            if car.boost <= 10 and ball.pos.y * bot.info.team_sign < 0 and dot_threat < 0.15:
                collect_center = ball.pos.y * bot.info.team_sign <= 0
                collect_small = closest_enemy.pos.y * bot.info.team_sign <= 0 or enemy_dist < 900
                pads = filter_pads(bot, bot.info.big_boost_pads, big_only=not collect_small, enemy_side=False,
                                   center=collect_center)
                bot.maneuver = CollectClosestBoostManeuver(bot, pads)

            # return home-ish
            return bot.drive.stay_at(bot, lerp(bot.info.own_goal.pos, ball.pos, 0.2), ball.pos)

