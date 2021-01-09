import math

from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from strategy.objective import Objective
from strategy.utility_system import UtilityState
from utility import predict, rendering
from utility.info import Field
from utility.rlmath import clip01, remap, lerp
from utility.vec import Vec3


class ClearBall(UtilityState):
    def __init__(self, bot):
        if bot.team == 0:
            # blue
            ra = 0.85 * math.pi
            la = 0.15 * math.pi
            self.aim_cone = AimCone(
                Vec3(math.cos(ra), math.sin(ra), 0),
                Vec3(math.cos(la), math.sin(la), 0)
            )
        else:
            # orange
            ra = -0.15 * math.pi
            la = -0.85 * math.pi
            self.aim_cone = AimCone(
                Vec3(math.cos(ra), math.sin(ra), 0),
                Vec3(math.cos(la), math.sin(la), 0)
            )

    def utility_score(self, bot) -> float:
        team_sign = bot.info.team_sign

        length = team_sign * Field.LENGTH2
        ball_own_half_01 = clip01(remap(-length, length, -0.8, 1.8, bot.info.ball.pos.y))

        reachable_ball = predict.ball_predict(bot, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        car_to_ball = reachable_ball.pos - bot.info.my_car.pos
        in_position = self.aim_cone.contains_direction(car_to_ball, math.pi / 8)

        obj_bonus = {
            Objective.UNKNOWN: 1,
            Objective.GO_FOR_IT: 1,
            Objective.FOLLOW_UP: 0,
            Objective.ROTATING: 0,
            Objective.SOLO: 1.0,
        }[bot.info.my_car.objective]

        return ball_own_half_01 * in_position * obj_bonus

    def run(self, bot) -> SimpleControllerState:
        car = bot.info.my_car
        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, predict.time_till_reach_ball(bot.info.my_car, bot.info.ball))
        hit_pos = bot.shoot.ball_when_hit.pos

        if bot.do_rendering:
            self.aim_cone.draw(bot, hit_pos, r=0, g=170, b=255)

        if bot.shoot.can_shoot:
            if bot.shoot.using_curve and bot.do_rendering:
                rendering.draw_bezier(bot, [car.pos, bot.shoot.curve_point, hit_pos])
            return shoot_controls

        else:
            # go home-ish
            own_goal = lerp(bot.info.own_goal.pos, bot.info.ball.pos, 0.5)
            return bot.drive.towards_point(bot, own_goal, target_vel=1460, slide=True, boost_min=0, can_keep_speed=True)
