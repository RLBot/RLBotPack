from maneuvers.strikes.double_touch import DoubleTouch
from maneuvers.dribbling.carry_and_flick import CarryAndFlick
from maneuvers.maneuver import Maneuver
from maneuvers.strikes.aerial_strike import AerialStrike, FastAerialStrike
from maneuvers.strikes.close_shot import CloseShot
from maneuvers.strikes.dodge_strike import DodgeStrike
from maneuvers.strikes.ground_strike import GroundStrike
from maneuvers.strikes.mirror_strike import MirrorStrike
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import vec3, dot
from rlutilities.simulation import Car, Ball
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import distance, ground_distance, align


def direct_shot(info: GameInfo, car: Car, target: vec3) -> Strike:
    dodge_shot = DodgeStrike(car, info, target)
    ground_shot = GroundStrike(car, info, target)

    if car.boost > 40:  # TODO
        # aerial_strike = AerialStrike(car, info, target)
        fast_aerial = FastAerialStrike(car, info, target)

        better_aerial_strike = min([fast_aerial], key=lambda strike: strike.intercept.time)

        if (
            better_aerial_strike.intercept.time < dodge_shot.intercept.time
            and better_aerial_strike.intercept.time - info.time < car.boost / 33
            and abs(better_aerial_strike.intercept.position.y - info.their_goal.center.y) > 500
        ):
            if ground_distance(better_aerial_strike.intercept, info.their_goal.center) < 3000:
                return DoubleTouch(better_aerial_strike)
            return better_aerial_strike

    if (
        dodge_shot.intercept.time < ground_shot.intercept.time - 0.1
        or ground_distance(dodge_shot.intercept, target) < 4000
        or distance(ground_shot.intercept.ball.velocity, car.velocity) < 500
        or is_opponent_close(info, 300)
    ):
        if (
            ground_distance(dodge_shot.intercept, target) < 4000
            and abs(dodge_shot.intercept.ground_pos[0]) < 2000
        ):
            return CloseShot(car, info, target)
        return dodge_shot
    return ground_shot


def any_shot(info: GameInfo, car: Car, target: vec3, intercept: Intercept, allow_dribble=False) -> Maneuver:
    ball = intercept.ball

    if (
        allow_dribble
        and (ball.position[2] > 100 or abs(ball.velocity[2]) > 250 or distance(car, info.ball) < 300)
        and abs(ball.velocity[2]) < 700
        and ground_distance(car, ball) < 1500
        and ground_distance(ball, info.my_goal.center) > 1000
        and ground_distance(ball, info.their_goal.center) > 1000
        and not is_opponent_close(info, info.ball.position[2] * 2 + 1000)
    ):
        return CarryAndFlick(car, info, target)

    direct = direct_shot(info, car, target)

    if not isinstance(direct, GroundStrike) and intercept.time < car.time + 4.0:
        alignment = align(car.position, ball, target)
        if alignment < -0.3 and abs(ball.position[1] - target[1]) > 3000:
            return MirrorStrike(car, info, target)

    return direct


def is_opponent_close(info: GameInfo, dist: float) -> bool:
    for opponent in info.get_opponents():
        if ground_distance(opponent.position + opponent.velocity * 0.5, info.ball) < dist:
            return True
    return False
