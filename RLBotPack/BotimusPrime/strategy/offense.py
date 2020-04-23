from maneuvers.dribbling.dribble import Dribble
from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike, FastAerialStrike
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.dodge_shot import DodgeShot
from maneuvers.strikes.ground_shot import GroundShot
from maneuvers.strikes.mirror_shot import MirrorShot
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from utils.game_info import GameInfo
from utils.intercept import Intercept
from utils.vector_math import distance, ground_distance, align


class Offense:

    def __init__(self, info: GameInfo):
        self.info = info
        self.allow_dribbles = False

    def direct_shot(self, car: Car, target: vec3) -> Maneuver:
        dodge_shot = DodgeShot(car, self.info, target)
        ground_shot = GroundShot(car, self.info, target)

        if car.boost > 40:
            aerial_strike = AerialStrike(car, self.info, target)
            fast_aerial = FastAerialStrike(car, self.info, target)

            if min(aerial_strike.intercept.time, fast_aerial.intercept.time) < dodge_shot.intercept.time:
                return min([aerial_strike, fast_aerial], key=lambda strike: strike.intercept.time)

        if (
            dodge_shot.intercept.time < ground_shot.intercept.time - 0.1
            or ground_distance(dodge_shot.intercept, target) < 4000
            or distance(ground_shot.intercept.ball.velocity, car.velocity) < 500
        ):
            if (
                distance(dodge_shot.intercept.ground_pos, target) < 4000
                and abs(dodge_shot.intercept.ground_pos[0]) < 3000
            ):
                return CloseShot(car, self.info, target)
            return dodge_shot
        return ground_shot

    def any_shot(self, car: Car, target: vec3, intercept: Intercept) -> Maneuver:
        ball = intercept.ball

        if (
            self.allow_dribbles
            and (100 < ball.position[2] or abs(ball.velocity[2]) > 300)
            and abs(ball.velocity[2]) < 1500
            and ground_distance(car, ball) < 1500
            and ground_distance(ball, self.info.my_goal.center) > 1000
        ):
            is_opponent_close = False
            for opponent in self.info.get_opponents(car):
                if ground_distance(opponent, car) < ball.position[2] * 2 + 1000:
                    is_opponent_close = True
                    break
            if not is_opponent_close:
                return Dribble(car, self.info, target)

        if align(car.position, ball, target) < 0.1 and abs(ball.position[1] - target[1]) > 3000:
            return MirrorShot(car, self.info, target)
        
        return self.direct_shot(car, target)
