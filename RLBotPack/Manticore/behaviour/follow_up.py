from rlbot.agents.base_agent import SimpleControllerState

from strategy.objective import Objective
from strategy.utility_system import UtilityState
from utility.info import Field
from utility.rlmath import clip01, is_closer_to_goal_than, lerp, argmin
from utility.vec import normalize, norm


class PrepareFollowUp(UtilityState):
    def utility_score(self, bot) -> float:

        car = bot.info.my_car
        ball = bot.info.ball

        follow_up_pos = bot.analyzer.ideal_follow_up_pos
        _, missing_follow_up_guy01 = argmin(bot.info.team_cars, lambda mate: 1.0 - clip01(norm(mate.pos - follow_up_pos) / Field.LENGTH2))
        attack_in_front = any(is_closer_to_goal_than(car.pos, mate.pos, car.team) for mate in bot.info.teammates if mate.objective == Objective.GO_FOR_IT)
        ball_in_front = is_closer_to_goal_than(car.pos, ball.pos, car.team)

        obj_bonus = {
            Objective.UNKNOWN: 0.5,
            Objective.GO_FOR_IT: 0,
            Objective.FOLLOW_UP: 1,
            Objective.ROTATING: 0,
            Objective.SOLO: 0.9,
        }[car.objective]

        return attack_in_front * ball_in_front * missing_follow_up_guy01 * bot.info.my_car.onsite * obj_bonus

    def run(self, bot) -> SimpleControllerState:

        car = bot.info.my_car
        ball = bot.info.ball
        dist_ball = norm(car.pos - ball.pos)
        target_pos = bot.analyzer.ideal_follow_up_pos
        dist_target = norm(car.pos - target_pos)

        return bot.drive.towards_point(
            bot,
            bot.analyzer.ideal_follow_up_pos,
            target_vel=dist_target * 0.8,
            slide=dist_target > 1000,
            can_dodge=False
        )
