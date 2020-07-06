from maneuvers.strikes.double_touch import DoubleTouch
from maneuvers.dribbling.carry_and_flick import CarryAndFlick
from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike, FastAerialStrike
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.ground_strike import GroundStrike
from maneuvers.strikes.mirror_strike import MirrorStrike
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import distance, ground_distance, align


class Offense:

    def __init__(self, info: GameInfo):
        self.info = info
        self.allow_dribbles = False

    def direct_shot(self, car: Car, target: vec3) -> Maneuver:
        dodge_shot = DodgeStrike(car, self.info, target)
        ground_shot = GroundStrike(car, self.info, target)

        if car.boost > 40:  # TODO
            aerial_strike = AerialStrike(car, self.info, target)
            fast_aerial = FastAerialStrike(car, self.info, target)

            better_aerial_strike = min([aerial_strike, fast_aerial], key=lambda strike: strike.intercept.time)

            if better_aerial_strike.intercept.time < dodge_shot.intercept.time:
                if ground_distance(better_aerial_strike.intercept, self.info.their_goal.center) < 5000:
                    return DoubleTouch(better_aerial_strike)
                return better_aerial_strike

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
            if not self.is_opponent_close(car, ball):
                return CarryAndFlick(car, self.info, target)

        alignment = align(car.position, ball, target)
        if alignment < 0.1 and abs(ball.position[1] - target[1]) > 3000:
            return MirrorStrike(car, self.info, target)
        
        # if 250 < ball.position[2] < 550 and self.is_opponent_close(car, ball):
        #     return DoubleJumpStrike(car, self.info, target)

        return self.direct_shot(car, target)

    def is_opponent_close(self, car, ball) -> bool:
        for opponent in self.info.get_opponents(car):
            if ground_distance(opponent, ball) < ball.position[2] * 2 + 1000:
                return True
        return False
