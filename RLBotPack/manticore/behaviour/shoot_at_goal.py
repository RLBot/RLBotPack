from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from maneuvers.collect_boost import CollectClosestBoostManeuver, filter_pads
from strategy.objective import Objective
from strategy.utility_system import UtilityState
from utility import predict, draw
from utility.easing import ease_out
from utility.info import Field, Ball
from utility.rlmath import clip01, remap, is_closer_to_goal_than, lerp
from utility.vec import norm, normalize, Vec3, xy, dot


class ShootAtGoal(UtilityState):
    def __init__(self):
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility_score(self, bot) -> float:

        car = bot.info.my_car
        ball = bot.info.ball

        my_hit_time = predict.time_till_reach_ball(car, ball)
        ball_soon = predict.ball_predict(bot, min(my_hit_time, 1.0))

        close_to_ball_01 = clip01(1.0 - norm(car.pos - ball_soon.pos) / 3500) ** 0.5  # FIXME Not great

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, ball))
        xy_ball_to_goal = xy(bot.info.opp_goal.pos - reachable_ball.pos)
        xy_car_to_ball = xy(reachable_ball.pos - bot.info.my_car.pos)
        in_position_01 = ease_out(clip01(dot(xy_ball_to_goal, xy_car_to_ball)), 0.5)

        # Chase ball right after kickoff. High right after kickoff
        kickoff_bias01 = max(0, 1 - bot.info.time_since_last_kickoff * 0.3) * float(bot.info.my_car.objective == Objective.SOLO)

        obj_bonus = {
            Objective.UNKNOWN: 1,
            Objective.GO_FOR_IT: 1,
            Objective.FOLLOW_UP: 0,
            Objective.ROTATING: 0,
            Objective.SOLO: 1,
        }[bot.info.my_car.objective]

        return clip01(close_to_ball_01 * in_position_01) * obj_bonus + kickoff_bias01

    def run(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball

        my_hit_time = predict.time_till_reach_ball(car, ball)
        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(car, ball))
        ball_to_goal_right = bot.info.opp_goal.right_post - reachable_ball.pos
        ball_to_goal_left = bot.info.opp_goal.left_post - reachable_ball.pos
        aim_cone = AimCone(ball_to_goal_right, ball_to_goal_left)
        shoot_controls = bot.shoot.with_aiming(bot, aim_cone, my_hit_time)

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
                draw.line(closest_enemy.pos, enemy_hit_pos, draw.red())
                return bot.drive.home(bot)

            draw.line(car.pos, offset_ball, draw.yellow())

            return bot.drive.towards_point(bot, offset_ball, target_vel=2200, slide=False, boost_min=0)

        elif len(bot.info.teammates) == 0 and not bot.shoot.aim_is_ok and hit_pos.y * -bot.info.team_sign > 4250 and abs(hit_pos.x) > 900 and not dist < 420:
            # hit_pos is an enemy corner and we are not close: Avoid enemy corners in 1s and just wait

            enemy_to_ball = normalize(hit_pos - closest_enemy.pos)
            wait_point = hit_pos + enemy_to_ball * enemy_dist  # a point 50% closer to the center of the field
            wait_point = lerp(wait_point, ball.pos + Vec3(0, bot.info.team_sign * 3000, 0), 0.5)

            draw.line(car.pos, wait_point, draw.yellow())

            return bot.drive.towards_point(bot, wait_point, norm(car.pos - wait_point), slide=False, can_keep_speed=True, can_dodge=False)

        elif bot.shoot.can_shoot:

            # Shoot !
            aim_cone.draw(bot.shoot.ball_when_hit.pos, r=0, b=0)
            if bot.shoot.using_curve:
                draw.bezier([car.pos, bot.shoot.curve_point, hit_pos], draw.color(100, 255, 100))
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
                    aim_cone.draw(bot.shoot.ball_when_hit.pos, b=0)
                    if bot.shoot.using_curve:
                        draw.bezier([car.pos, bot.shoot.curve_point, hit_pos], draw.color(100, 255, 100))
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

