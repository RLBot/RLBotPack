from rlbot.agents.base_agent import SimpleControllerState

from strategy.objective import Objective
from strategy.utility_system import UtilityState
from util.info import Field
from util.rlmath import clip01, is_closer_to_goal_than, lerp, argmin
from util.vec import normalize, norm


class PrepareFollowUp(UtilityState):
    def utility_score(self, bot) -> float:

        car = bot.info.my_car
        ball = bot.info.ball

        half_way = lerp(bot.info.own_goal.pos, ball.pos, 0.5)
        _, missing_center_guy01 = argmin(bot.info.team_cars, lambda mate: 1.0 - clip01(norm(mate.pos - half_way) / Field.LENGTH2))
        attack_in_front = any(is_closer_to_goal_than(car.pos, mate.pos, car.team) for mate in bot.info.teammates if mate.objective == Objective.GO_FOR_IT)
        ball_in_front = is_closer_to_goal_than(car.pos, ball.pos, car.team)

        obj_bonus = {
            Objective.UNKNOWN: 0,
            Objective.GO_FOR_IT: 0,
            Objective.FOLLOW_UP: 0.23,
            Objective.ROTATE_BACK_OR_DEF: 0,
        }[car.objective]

        return attack_in_front * ball_in_front * missing_center_guy01 + obj_bonus

    def run(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball
        half_way = lerp(bot.info.own_goal.pos, ball.pos, 0.5)
        dist_ball = norm(car.pos - ball.pos)

        return bot.drive.towards_point(
            bot,
            half_way,
            target_vel=dist_ball * 0.3,
            slide=dist_ball > 1500,
            can_dodge=False
        )
