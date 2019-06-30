
from RLUtilities.GameInfo import GameInfo
from RLUtilities.LinearAlgebra import *
from RLUtilities.Simulation import Car, Ball

from utils.vector_math import *
from utils.math import *
from utils.misc import *
from utils.intercept import Intercept, AerialIntercept


from maneuvers.kit import Maneuver
from maneuvers.dribbling.dribble import Dribble
from maneuvers.air.aerial import Aerial
from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.strike import Strike
from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.mirror_shot import MirrorShot
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.aerial_shot import AerialShot
from maneuvers.strikes.wall_shot import WallShot
from maneuvers.strikes.wall_dodge_shot import WallDodgeShot
from maneuvers.shadow_defense import ShadowDefense




class Offense:

    def __init__(self, info: GameInfo):
        self.info = info

    def wall_shot(self, car: Car, target: vec3) -> Maneuver:
        ground_shot = WallShot(car, self.info, target)
        dodge_shot = WallDodgeShot(car, self.info, target)

        if dodge_shot.intercept.time < ground_shot.intercept.time - 0.1:
            return dodge_shot

        return ground_shot


    def direct_shot(self, car: Car, target: vec3) -> Maneuver:
        dodge_shot = DodgeShot(car, self.info, target)
        ground_shot = GroundShot(car, self.info, target)

        if (
            dodge_shot.intercept.time < ground_shot.intercept.time - 0.1 \
            or distance(dodge_shot.intercept.ground_pos, target) < 4000 \
            or (dot(direction(ground_shot.intercept.ground_pos, car), ground_shot.intercept.ball.vel) < -0.2 \
            and norm(ground_shot.intercept.ball.vel) > 500)
        ):
            if distance(dodge_shot.intercept.ground_pos, target) < 4000\
            and abs(dodge_shot.intercept.ground_pos[0]) < 3000:
                return CloseShot(car, self.info, target)
            return dodge_shot
        return ground_shot

 
    def high_shot(self, car: Car, target: vec3) -> Maneuver:
        direct_shot = self.direct_shot(car, target)

        wall_shot = self.wall_shot(car, target)
        if wall_shot.intercept.is_viable and wall_shot.intercept.time < direct_shot.intercept.time:
            return wall_shot

        aerial = AerialShot(car, self.info, target)
        if (
            aerial.intercept.is_viable
            and car.boost > aerial.intercept.ball.pos[2] / 50 + 5
            and aerial.intercept.time < direct_shot.intercept.time
            and not self.info.about_to_score
            and abs(aerial.intercept.ball.pos[1] - target[1]) > 2000
        ):
            return aerial

        return direct_shot
        

    def any_shot(self, car: Car, target: vec3, intercept: Intercept) -> Maneuver:
        ball = intercept.ball

        if 120 < ball.pos[2] < 1500 and abs(ball.vel[2]) < 1200 and ground_distance(car, intercept) < 1000:
            is_opponent_close = False
            for opponent in self.info.opponents:
                if ground_distance(opponent, car) < ball.pos[2] * 10 + 500:
                    is_opponent_close = True
                    break
            if not is_opponent_close:
                return Dribble(car, self.info, target)


        if ball.pos[2] > 300 or abs(ball.vel[2]) > 500:
            return self.high_shot(car, target)

        if align(car.pos, ball, target) < 0.1 and abs(ball.pos[1]) < 3000 and abs(ball.pos[0]) > 1000:
            return MirrorShot(car, self.info, target)
        
        return self.direct_shot(car, target)


    def shot_or_position(self, car: Car, target: vec3, intercept: Intercept) -> Maneuver:
        strike = self.any_shot(car, target, intercept)
        if not isinstance(strike, Strike):
            return strike
        
        distance_to_target = distance(strike.intercept.ground_pos, target)
        shift = clamp(distance_to_target / 6, 100, 800)

        if not strike.intercept.is_viable or distance(strike.intercept.ground_pos, car) < shift:
            
            return ShadowDefense(car, self.info, strike.intercept.ground_pos, shift)
        return strike

    def double_tap(self, car: Car, target: vec3) -> Maneuver:
        if car.boost < 5:
            return None
        predicate = lambda car, ball: (
            abs(ball.pos[0]) < 1000
            and ball.pos[2] > 400
            and distance(ball, target) < 4000
            and align(car.pos, ball, target) > 0.3
        )
        intercept = AerialIntercept(car, self.info.ball_predictions, predicate)
        if intercept.is_viable and car.boost > (intercept.time - car.time) * 5:
            target_pos = intercept.ball.pos + direction(target, intercept.ball.pos) * 60
            return Aerial(car, target_pos, intercept.time)