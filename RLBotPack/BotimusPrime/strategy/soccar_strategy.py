from rlbot.agents.base_agent import GameTickPacket

from utils.game_info import GameInfo
from rlutilities.linear_algebra import *
from rlutilities.simulation import Car, Ball

from utils.vector_math import *
from utils.math import *
from utils.misc import *
from utils.intercept import Intercept
from utils.arena import Arena

from tools.drawing import DrawingTool

from maneuvers.kit import Maneuver
from maneuvers.kickoffs.kickoff import Kickoff
from maneuvers.kickoffs.diagonal import DiagonalKickoff
from maneuvers.driving.stop import Stop
from maneuvers.air.fast_recovery import FastRecovery
from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.strike import Strike
from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.aerial_strike import AerialStrike
from maneuvers.refuel import Refuel
from maneuvers.shadow_defense import ShadowDefense

from strategy.offense import Offense

import time

#This file is a Wintertide-deadline mess and definitely not something you should learn from..

class SoccarStrategy:
    def __init__(self, info: GameInfo, drawing_tool: DrawingTool):
        self.draw = drawing_tool
        self.info = info
        self.offense = Offense(info)
        self.aggresivity = 0
        self.packet: GameTickPacket = None

    def get_team_scores(self):
        our_score = 0
        their_score = 0
        
        for team in self.packet.teams:
            if team.team_index == self.info.my_car.team:
                our_score = team.score
            else:
                their_score = team.score

        return our_score, their_score

    def best_intercept(self, cars, max_height=9999) -> Intercept:
        best_intercept = None
        best_car = None

        for car in cars:
            intercept = Intercept(car, self.info.ball_predictions, lambda car, ball: ball.position[2] < max_height)
            if best_intercept is None or intercept.time <= best_intercept.time:
                best_intercept = intercept
                best_car = car

        if best_intercept is None:
            best_car = Car()
            best_intercept = Intercept(best_car, [])

        return best_intercept, best_car

    def when_airborne(self) -> Maneuver:
        # double_tap = self.offense.double_tap(self.info.my_car, self.info.their_goal.center)
        # if double_tap is not None:
        #     return double_tap
        return FastRecovery(self.info.my_car)

    def clear_into_corner(self, my_hit: Intercept) -> DodgeShot:
        car = self.info.my_car
        my_goal = self.info.my_goal.center
        corners = [my_goal + vec3(Arena.size[0], 0, 0), my_goal - vec3(Arena.size[0], 0, 0)]
        corner = Strike.pick_easiest_target(car, my_hit.ball, corners)
        corner[1] *= 0.8
        if abs(corner[1]) > abs(car.position[1]):
            corner[1] = car.position[1]

        return DodgeShot(car, self.info, corner)

    def choose_maneuver(self):
        info = self.info
        offense = self.offense

        ball = info.ball
        car = info.my_car

        my_score, their_score = self.get_team_scores()

        their_goal = ground(info.their_goal.center)
        my_goal = ground(info.my_goal.center)

        
        my_hit = Intercept(car, info.ball_predictions)
        their_best_hit, opponent = self.best_intercept(info.opponents, 500)
        
        self.draw.group("intersects")
        self.draw.color(self.draw.cyan)
        self.draw.crosshair(my_hit.position)
        self.draw.color(self.draw.red)
        self.draw.crosshair(their_best_hit.position)
        

        # if my_score > their_score + 2:
        #     self.aggresivity = 5
        # else:
        #     self.aggresivity = 0

        # if their_score > my_score:
        #     if self.packet.game_info.game_time_remaining < 60:
        #         self.aggresivity = 5
        #     if self.packet.game_info.game_time_remaining < 30:
        #         self.aggresivity = 30

        should_commit = True
        if info.teammates:
            best_team_intercept, _ = self.best_intercept(info.teammates, 500)
            if best_team_intercept.time < my_hit.time - 0.05:
                should_commit = False


        if not car.on_ground:
            return self.when_airborne()

        # kickoff
        if should_commit and ball.position[0] == 0 and ball.position[1] == 0:
            return Kickoff(car, info)

        # dont save our own shots
        if info.about_to_score:
            if info.time_of_goal < their_best_hit.time - 2:
                return Stop(car)

        # save
        if info.about_to_be_scored_on:

            if align(car.position, my_hit.ball, their_goal) > -0.2:

                any_shot = offense.any_shot(car, their_goal, my_hit)

                if (not isinstance(any_shot, Strike) or their_best_hit.time < any_shot.intercept.time + 0.5) \
                and align(car.position, my_hit.ball, their_goal) < 0.6:
                
                    return DodgeStrike(car, info, their_goal)
                return any_shot

            return self.clear_into_corner(my_hit)


        # fallback
        if align(car.position, my_hit.ball, my_goal) > 0.2:
            if ground_distance(my_hit, my_goal) < 4000 and should_commit and abs(car.position[1]) < abs(my_hit.position[1]):
                return self.clear_into_corner(my_hit)
            return ShadowDefense(car, info, my_hit.ground_pos, 6000)

        # clear
        if (
            should_commit
            and ground_distance(my_hit, my_goal) < 3500
            and abs(my_hit.position[0]) < 3000
            and ground_distance(car, my_goal) < 2500
        ):

            if align(car.position, my_hit.ball, their_goal) > -0.1:

                any_shot = offense.any_shot(car, their_goal, my_hit)

                if (not isinstance(any_shot, Strike) or their_best_hit.time < any_shot.intercept.time + 0.5) \
                and align(car.position, my_hit.ball, their_goal) < 0.6:
                
                    return DodgeStrike(car, info, their_goal)
                return any_shot
            return self.clear_into_corner(my_hit)


        # double tap 
        if should_commit and car.position[2] > 1000:
            double_tap = offense.double_tap(car, their_goal)
            if double_tap is not None:
                return double_tap

        # 1v1
        if not info.teammates:
            if distance(their_best_hit.ground_pos, their_goal) < distance(their_best_hit.ground_pos, my_goal):
                opponents_align = -align(opponent.position, their_best_hit.ball, their_goal)
            else:
                opponents_align = align(opponent.position, their_best_hit.ball, my_goal)

            # I can get to ball faster than them
            if should_commit and my_hit.time < their_best_hit.time - 0.8:
                strike = offense.any_shot(car, their_goal, my_hit)

                if not isinstance(strike, Strike):
                    return strike

                if strike.intercept.time < their_best_hit.time - 0.8 \
                and (not info.about_to_score or strike.intercept.time < info.time_of_goal - 1):

                    if strike.intercept.time - car.time > 4 and car.boost < 30 \
                    and distance(strike.intercept.ground_pos, their_goal) > 3000 and distance(their_best_hit.ground_pos, my_goal) > 5000:

                        return Refuel(car, info, my_hit.ground_pos)

                    if abs(strike.intercept.ground_pos[0]) > Arena.size[0] - 800 and car.boost < 30:

                        return Refuel(car, info, my_hit.ground_pos)

                    if abs(strike.intercept.ball.position[1] - their_goal[1]) > 300 or ground_distance(strike.intercept, their_goal) < 900:
                        return strike

            # they are out of position
            if (
                should_commit
                and opponents_align < -0.1 - self.aggresivity / 20 
                and my_hit.time < their_best_hit.time - opponents_align * 1.5
            ):

                strike = offense.any_shot(car, their_goal, my_hit)

                if not isinstance(strike, Strike) or strike.intercept.is_viable \
                and (not info.about_to_score or strike.intercept.time < info.time_of_goal - 0.5):

                    if (
                        car.boost < 40
                        and (distance(my_hit, their_goal) > 5000 or abs(my_hit.position[0]) > Arena.size[0] - 1500)
                        and distance(opponent, their_best_hit) > 3000
                    ):
                        return Refuel(car, info, my_hit.ground_pos)

                    if not isinstance(strike, Strike) or abs(strike.intercept.ball.position[1] - their_goal[1]) > 300 or ground_distance(strike.intercept, their_goal) < 900:
                        return strike

            if distance(their_best_hit.ball, my_goal) > 7000 and \
                (distance(their_best_hit, opponent) > 3000 or align(opponent.position, their_best_hit.ball, my_goal) < 0) and car.boost < 30:
                return Refuel(car, info, my_hit.ground_pos)

            if car.boost < 35 and distance(their_best_hit, opponent) > 3000:
                refuel = Refuel(car, info, my_hit.ground_pos)
                if estimate_time(car, refuel.pad.position, 1400) < 1.5:
                    return refuel

        # teamplay
        else:
            if should_commit:
                return offense.any_shot(car, their_goal, my_hit)

            if car.boost < 50:
                return Refuel(car, info, my_goal)

        if opponents_align < 0:
            return offense.any_shot(car, their_goal, my_hit)

        shadow_distance = 5500
        shadow_distance -= self.aggresivity * 500
        shadow_distance = max(shadow_distance, 3000)
        return ShadowDefense(car, info, their_best_hit.ground_pos, shadow_distance)
