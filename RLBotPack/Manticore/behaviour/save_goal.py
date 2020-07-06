from rlbot.agents.base_agent import SimpleControllerState

from controllers.aim_cone import AimCone
from strategy.objective import Objective
from strategy.utility_system import UtilityState
from util import predict
from util.info import Ball, Goal
from util.rlmath import sign, clip
from util.vec import Vec3, norm


class SaveGoal(UtilityState):
    def __init__(self, bot):
        team_sign = bot.info.team_sign
        self.aim_cone = None
        self.ball_to_goal_right = None
        self.ball_to_goal_left = None

    def utility_score(self, bot) -> float:
        team_sign = bot.info.team_sign
        ball = bot.info.ball

        ball_to_goal = bot.info.own_goal.pos - ball.pos
        too_close = norm(ball_to_goal) < Goal.WIDTH2 + Ball.RADIUS

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        hits_goal = hits_goal_prediction.happens and sign(ball.vel.y) == team_sign and hits_goal_prediction.time < 3

        obj_bonus = {
            Objective.UNKNOWN: 0,
            Objective.GO_FOR_IT: 0.2,
            Objective.FOLLOW_UP: 0,
            Objective.ROTATE_BACK_OR_DEF: 0.1,
        }[bot.info.my_car.objective]

        return float(hits_goal or too_close) + obj_bonus

    def run(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball

        hits_goal_prediction = predict.will_ball_hit_goal(bot)
        reach_time = clip(predict.time_till_reach_ball(car, ball), 0, hits_goal_prediction.time - 0.5)
        reachable_ball = predict.ball_predict(bot, reach_time)
        self.ball_to_goal_right = bot.info.own_goal.right_post - reachable_ball.pos
        self.ball_to_goal_left = bot.info.own_goal.left_post - reachable_ball.pos
        self.aim_cone = AimCone(self.ball_to_goal_left, self.ball_to_goal_right)

        if bot.do_rendering:
            self.aim_cone.draw(bot, reachable_ball.pos, r=200, g=0, b=160)

        shoot_controls = bot.shoot.with_aiming(bot, self.aim_cone, reach_time)

        if not bot.shoot.can_shoot:
            # Go home
            return bot.drive.home(bot)
        else:
            return shoot_controls
