from maneuvers.strikes.double_touch import DoubleTouch
from maneuvers.dribbling.carry_and_flick import CarryAndFlick
from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike, FastAerialStrike
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.ground_strike import GroundStrike
from maneuvers.strikes.mirror_strike import MirrorStrike
from rlutilities.linear_algebra import vec3
from rlutilities.simulation import Car, Ball
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import distance, ground_distance, align


def direct_shot(info: GameInfo, car: Car, target: vec3) -> Maneuver:
    dodge_shot = DodgeStrike(car, info, target)
    ground_shot = GroundStrike(car, info, target)

    if car.boost > 40:  # TODO
        aerial_strike = AerialStrike(car, info, target)
        fast_aerial = FastAerialStrike(car, info, target)

        better_aerial_strike = min([aerial_strike, fast_aerial], key=lambda strike: strike.intercept.time)

        if better_aerial_strike.intercept.time < dodge_shot.intercept.time:
            if ground_distance(better_aerial_strike.intercept, info.their_goal.center) < 5000:
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
            return CloseShot(car, info, target)
        return dodge_shot
    return ground_shot


def any_shot(info: GameInfo, car: Car, target: vec3, intercept: Intercept, allow_dribble=False) -> Maneuver:
    ball = intercept.ball

    if (
        allow_dribble
        and (100 < ball.position[2] or abs(ball.velocity[2]) > 300)
        and abs(ball.velocity[2]) < 1500
        and ground_distance(car, ball) < 1500
        and ground_distance(ball, info.my_goal.center) > 1000
    ):
        if not is_opponent_close(info, car):
            return CarryAndFlick(car, info, target)

    alignment = align(car.position, ball, target)
    if alignment < 0.1 and abs(ball.position[1] - target[1]) > 3000:
        return MirrorStrike(car, info, target)

    # if 250 < ball.position[2] < 550 and is_opponent_close(car, ball):
    #     return DoubleJumpStrike(car, info, target)

    return direct_shot(info, car, target)


def is_opponent_close(info: GameInfo, car: Car) -> bool:
    for opponent in info.get_opponents(car):
        if ground_distance(opponent, info.ball) < info.ball.position[2] * 2 + 1000:
            return True
    return False
