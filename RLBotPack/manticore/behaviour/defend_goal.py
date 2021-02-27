from rlbot.agents.base_agent import SimpleControllerState

from maneuvers.collect_boost import CollectClosestBoostManeuver
from strategy.objective import Objective
from strategy.utility_system import UtilityState
from utility.info import Field
from utility.rlmath import clip01, argmin
from utility.vec import norm


class DefendGoal(UtilityState):
    def utility_score(self, bot) -> float:

        car = bot.info.my_car

        if len(bot.info.teammates) == 0:
            team_committed01 = 0
            no_defence01 = 1
        else:
            mates = bot.info.teammates
            sum_pos = mates[0].pos + mates[0].vel * 0.5
            for mate in mates[1:]:
                sum_pos += mate.pos + mate.vel * 0.5
            avg_pos = sum_pos / len(mates)
            team_committed01 = clip01(norm(avg_pos - bot.info.own_goal.pos) / Field.LENGTH)
            no_defence01 = clip01(argmin(mates, lambda mate: norm(mate.pos - bot.info.own_goal.pos))[1] / 1000)

        dist_to_ball01 = clip01(norm(car.pos - bot.info.ball.pos) / Field.LENGTH2)

        obj_bonus = {
            Objective.UNKNOWN: 1.0,
            Objective.GO_FOR_IT: 0,
            Objective.FOLLOW_UP: 0,
            Objective.ROTATING: 1.0,
            Objective.SOLO: 1.0,
        }[car.objective]

        return 0.85 * team_committed01 * dist_to_ball01 * no_defence01 * obj_bonus

    def run(self, bot) -> SimpleControllerState:
        ball = bot.info.ball
        if norm(ball.pos - bot.info.own_goal.pos) / Field.LENGTH > bot.info.my_car.boost / 100:
            bot.maneuver = CollectClosestBoostManeuver(bot)
        return bot.drive.home(bot)
