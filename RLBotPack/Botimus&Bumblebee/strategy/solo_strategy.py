from maneuvers.general_defense import GeneralDefense
from maneuvers.recovery import Recovery
from maneuvers.refuel import Refuel
from rlutilities.simulation import Car
from strategy import offense, defense, kickoffs
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import align, ground, ground_distance


def choose_maneuver(info: GameInfo, my_car: Car):
    ball = info.ball
    their_goal = ground(info.their_goal.center)
    my_goal = ground(info.my_goal.center)
    opponents = info.get_opponents(my_car)

    # recovery
    if not my_car.on_ground:
        return Recovery(my_car)

    # kickoff
    if ball.position[0] == 0 and ball.position[1] == 0:
        return kickoffs.choose_kickoff(info, my_car)

    info.predict_ball()

    my_intercept = Intercept(my_car, info.ball_predictions)
    their_intercepts = [Intercept(opponent, info.ball_predictions) for opponent in opponents]
    their_best_intercept = min(their_intercepts, key=lambda i: i.time)
    opponent = their_best_intercept.car

    # if ball is in a dangerous position, clear it
    if ground_distance(their_best_intercept, my_goal) < 2000:
        return defense.any_clear(info, my_intercept.car)

    # if I'm low on boost and the ball is not near my goal, go for boost
    if my_car.boost < 20:
        return Refuel(my_car, info, my_intercept.position)

    # if they can hit the ball sooner than me and they aren't out of position, wait in defense
    if (
        their_best_intercept.time < my_intercept.time
        and align(opponent.position, their_best_intercept.ball, my_goal) > 0
    ):
        return GeneralDefense(my_car, info, my_intercept.position, 7000)

    # if not completely out of position, go for a shot
    if align(my_intercept.car.position, my_intercept.ball, their_goal) > 0:
        return offense.any_shot(info, my_intercept.car, their_goal, my_intercept, allow_dribble=True)

    # if ball near my goal, clear it
    if ground_distance(my_intercept, my_goal) < 4000:
        return defense.any_clear(info, my_intercept.car)

    # fallback
    return GeneralDefense(my_car, info, my_intercept.position, 7000)
