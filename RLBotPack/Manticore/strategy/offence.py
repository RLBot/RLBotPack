from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from util import predict, rendering
from util.info import Field
from util.rlmath import clip01, lerp
from util.vec import norm, Vec3, normalize


class OffenceState:
    def __init__(self):
        pass

    def exec(self, bot):
        pred_ball = predict.ball_predict(bot, bot.info.my_car.reach_ball_time)

        # On a scale from 0 to 1, how much is this a clear?
        clear01 = clip01(norm(bot.info.opp_goal.pos - pred_ball.pos) / Field.LENGTH) ** 2

        ts = bot.info.team_sign
        right = lerp(bot.info.opp_goal.right_post, Vec3(ts * Field.WIDTH2, ts * (Field.LENGTH2 + 300), 0), clear01)
        left = lerp(bot.info.opp_goal.left_post, Vec3(-ts * Field.WIDTH2, ts * (Field.LENGTH2 + 300), 0), clear01)

        ball_to_right = right - pred_ball.pos
        ball_to_left = left - pred_ball.pos


        aim_cone = AimCone(ball_to_right, ball_to_left)
        shot_ctrls = bot.shoot.with_aiming(
            bot,
            aim_cone,
            bot.info.my_car.reach_ball_time
        )

        if bot.do_rendering:
            if bot.shoot.can_shoot:
                aim_cone.draw(bot, bot.shoot.ball_when_hit.pos, b=0, r=0)

        if not bot.shoot.can_shoot:
            # We can't shoot on target
            if len(bot.info.teammates) != 0:
                # Consider passing
                for mate in bot.info.teammates:
                    point_in_front_of_mate = lerp(mate.pos, bot.info.opp_goal.pos, 0.5)
                    shot_ctrls = bot.shoot.towards(bot, point_in_front_of_mate, bot.info.my_car.reach_ball_time)
                    if bot.shoot.can_shoot:
                        if bot.do_rendering:
                            rendering.draw_cross(bot, point_in_front_of_mate, bot.renderer.green())
                        return shot_ctrls

            # Atba with bias I guess
            if bot.do_rendering:
                bot.renderer.draw_line_3d(bot.info.my_car.pos, pred_ball.pos, bot.renderer.red())
            return bot.shoot.any_touch(bot, bot.info.my_car.reach_ball_time)

            # # We are out of position, start rotating back
            # own_goal = lerp(bot.info.own_goal.pos, bot.info.ball.pos, 0.5)
            # return bot.drive.towards_point(
            #     bot,
            #     own_goal,
            #     target_vel=1460,
            #     slide=False,
            #     boost_min=0,
            #     can_keep_speed=True
            # )
        else:
            # Shoot!
            if bot.shoot.using_curve and bot.do_rendering:
                rendering.draw_bezier(bot, [bot.info.my_car.pos, bot.shoot.curve_point, bot.shoot.ball_when_hit.pos])
            return shot_ctrls
