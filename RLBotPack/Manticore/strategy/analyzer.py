from strategy.objective import Objective
from utility import predict, rendering
from utility.easing import lin_fall, ease_out
from utility.rlmath import argmin, argmax, clip01
from utility.vec import Vec3, xy
from utility.vec import norm, normalize, dot


class GameAnalyzer:
    def __init__(self):
        self.opp_closest_to_ball = None
        self.opp_closest_to_ball_dist = 99999
        self.car_with_possession = None
        self.ally_with_possession = None
        self.opp_with_possession = None
        self.first_to_reach_ball = None
        self.ideal_follow_up_pos = Vec3()

    def update(self, bot):
        ball = bot.info.ball

        # Find closest foe to ball
        self.opp_closest_to_ball, self.opp_closest_to_ball_dist = argmin(bot.info.opponents, lambda opp: norm(opp.pos - ball.pos))

        # Possession and on/off-site
        self.car_with_possession = None
        self.ally_with_possession = None
        self.opp_with_possession = None
        for car in bot.info.cars:

            # Effective position
            car.effective_pos = car.pos + xy(car.vel) * 0.8

            # On site
            car_to_ball = ball.pos - car.pos
            car_to_ball_unit = normalize(car_to_ball)
            car.onsite = dot(Vec3(y=-car.team_sign), car_to_ball_unit)

            # Reach ball time
            car.reach_ball_time = predict.time_till_reach_ball(car, ball)
            reach01 = 1 - 0.9 * lin_fall(car.reach_ball_time, 4) ** 0.5

            # Possession
            point_in_front = car.pos + car.vel * 0.5
            ball_point_dist = norm(ball.pos - point_in_front)
            dist01 = 1000 / (1000 + ball_point_dist)  # Halved after 1000 uu of dist, 1/3 at 2000
            in_front01 = (dot(car.forward, car_to_ball_unit) + 1) / 2.0
            car.possession = dist01 * in_front01 * reach01
            if self.car_with_possession is None or car.possession > self.car_with_possession.possession:
                self.car_with_possession = car
            if car.team == bot.team and (self.ally_with_possession is None or car.possession > self.ally_with_possession.possession):
                self.ally_with_possession = car
            if car.team != bot.team and (self.opp_with_possession is None or car.possession > self.opp_with_possession.possession):
                self.opp_with_possession = car

        # Objectives
        if len(bot.info.team_cars) == 1:
            # No team mates. No roles
            bot.info.my_car.objective = bot.info.my_car.last_objective = Objective.SOLO
            return

        for car in bot.info.cars:
            car.last_objective = car.objective
            car.objective = Objective.UNKNOWN

        attacker, attacker_score = argmax(bot.info.team_cars,
                                          lambda ally: ((1.0 if ally.last_objective == Objective.GO_FOR_IT else 0.8)
                                                        * ease_out(0.2 + 0.8 * ally.boost / 100, 2)  # 50 boost is 0.85, 0 boost is 0.2
                                                        * ally.possession
                                                        * ally.got_it_according_to_quick_chat_01(bot.info.time)
                                                        * (1.0 if ally.onsite else 0.5)
                                                        * (0 if ally.is_demolished else 1)))

        attacker.objective = Objective.GO_FOR_IT
        self.ideal_follow_up_pos = xy(ball.pos + bot.info.own_goal.pos) * 0.5
        follower, follower_score = argmax([ally for ally in bot.info.team_cars if ally.objective == Objective.UNKNOWN],
                                          lambda ally: (1.0 if ally.last_objective == Objective.FOLLOW_UP else 0.8)
                                                        * ease_out(0.2 * 0.8 * ally.boost / 100, 2)
                                                        * (1 + ally.onsite / 2)
                                                        * lin_fall(norm(ally.effective_pos - self.ideal_follow_up_pos), 3000)
                                                        * (0 if ally.is_demolished else 1))
        if bot.index == 0:
            bot.renderer.draw_string_2d(400, 600, 1, 1, str(attacker_score), bot.renderer.blue())
        if follower is not None:
            follower.objective = Objective.FOLLOW_UP
        for car in bot.info.team_cars:
            if car.objective == Objective.UNKNOWN:
                car.objective = Objective.ROTATING
