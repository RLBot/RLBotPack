from rlbot.agents.base_agent import SimpleControllerState

from behaviours.moves import AimCone
from behaviours.utsystem import Choice
from maneuvers.collect_boost import CollectClosestBoostManeuver, filter_pads
from util import predict, rendering
from util.info import Field, Ball
from util.rlmath import clip01, remap, is_closer_to_goal_than, lerp
from util.vec import norm, normalize, Vec3


class ShootAtGoal(Choice):
    def __init__(self):
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility(self, bot) -> float:
        ball_soon = predict.ball_predict(bot, 1)

        arena_length2 = bot.info.team_sign * Field.LENGTH / 2
        own_half_01 = clip01(remap(arena_length2, -arena_length2, 0.0, 1.1, ball_soon.pos.y))

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        self.ball_to_goal_right = bot.info.enemy_goal_right - reachable_ball.pos
        self.ball_to_goal_left = bot.info.enemy_goal_left - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_right, self.ball_to_goal_left)
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball)

        return clip01(own_half_01 + 0.1 * in_position)

    def exec(self, bot) -> SimpleControllerState:

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
            offset_ball = hit_pos + goal_to_ball * Ball.RADIUS * 0.9

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, offset_ball, bot.renderer.yellow())

            return bot.drive.go_towards_point(bot, offset_ball, target_vel=2200, slide=False, boost_min=0)

        elif not bot.shoot.aim_is_ok and hit_pos.y * -bot.info.team_sign > 4350 and abs(hit_pos.x) > 900 and not dist < 450:
            # hit_pos is an enemy corner and we are not close: Avoid enemy corners and just wait

            enemy_to_ball = normalize(hit_pos - closest_enemy.pos)
            wait_point = hit_pos + enemy_to_ball * enemy_dist  # a point 50% closer to the center of the field
            wait_point = lerp(wait_point, ball.pos + Vec3(0, bot.info.team_sign * 3000, 0), 0.5)

            if bot.do_rendering:
                bot.renderer.draw_line_3d(car.pos, wait_point, bot.renderer.yellow())

            return bot.drive.go_towards_point(bot, wait_point, norm(car.pos - wait_point), slide=False, can_keep_speed=True, can_dodge=False)

        elif not bot.shoot.can_shoot:
            if car.boost == 0:

                collect_center = ball.pos.y * bot.info.team_sign <= 0
                collect_small = closest_enemy.pos.y * bot.info.team_sign <= 0
                pads = filter_pads(bot, bot.info.big_boost_pads, big_only=not collect_small, enemy_side=False, center=collect_center)
                bot.maneuver = CollectClosestBoostManeuver(bot, pads)
            # return home
            return bot.drive.go_home(bot)

        else:
            # Shoot !
            if bot.shoot.using_curve and bot.do_rendering:
                rendering.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])
            return shoot_controls
