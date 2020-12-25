from rlbot.agents.base_agent import SimpleControllerState

from utility.rlmath import lerp, inv_lerp
from utility.vec import norm, normalize, proj_onto_size, proj_onto


class FollowUpState:
    def __init__(self):
        pass

    def exec(self, bot):

        goal_to_ball = bot.info.ball.pos - bot.info.own_goal.pos
        goal_to_car = bot.info.my_car.pos - bot.info.own_goal.pos

        car_prj = proj_onto(goal_to_car, goal_to_ball)
        target = lerp(bot.info.own_goal.pos + car_prj, lerp(bot.info.ball.pos, bot.info.opp_goal.pos, 0.4), 0.08)

        if bot.do_rendering:
            bot.renderer.draw_line_3d(bot.info.my_car.pos, target, bot.renderer.purple())

        speed = max((norm(bot.info.my_car.pos - bot.info.ball.pos) - 900) * 0.6, 100)

        return bot.drive.towards_point(
            bot,
            target,
            target_vel=speed,
            slide=True,
            boost_min=0,
            can_keep_speed=norm(bot.info.my_car.pos - bot.info.ball.pos) > 3000,
            can_dodge=True,
            wall_offset_allowed=125
        )
