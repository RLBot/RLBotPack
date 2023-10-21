from maneuvers.general_defense import GeneralDefense
from maneuvers.recovery import Recovery
from maneuvers.pickup_boostpad import PickupBoostPad
from rlutilities.simulation import Car
from strategy import offense, kickoffs, defense
from strategy.boost_management import choose_boostpad_to_pickup
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.vector_math import align, ground, distance, ground_distance


def choose_maneuver(info: GameInfo, my_car: Car):
    ball = info.ball
    teammates = info.get_teammates(my_car)
    my_team = [my_car] + teammates
    their_goal = ground(info.their_goal.center)
    my_goal = ground(info.my_goal.center)

    # recovery
    if not my_car.on_ground:
        return Recovery(my_car)

    # kickoff
    if ball.position[0] == 0 and ball.position[1] == 0:

        # if I'm nearest (or tied) to the ball, go for kickoff
        if distance(my_car, ball) == min(distance(car, ball) for car in my_team):
            return kickoffs.choose_kickoff(info, my_car)

    if my_car.boost < 20:
        best_boostpad = choose_boostpad_to_pickup(info, my_car)
        if best_boostpad is not None:
            return PickupBoostPad(my_car, best_boostpad)

    info.predict_ball()

    my_intercept = Intercept(my_car, info.ball_predictions)
    teammates_intercepts = [Intercept(mate, info.ball_predictions) for mate in teammates]
    our_intercepts = teammates_intercepts + [my_intercept]

    good_intercepts = [i for i in our_intercepts if align(i.car.position, i.ball, their_goal) > 0.0]
    if good_intercepts:
        best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
    else:
        best_intercept = min(our_intercepts, key=lambda i: distance(i.car, my_goal))
        if ground_distance(my_car, my_goal) < 2000:
            best_intercept = my_intercept

    if best_intercept is my_intercept:
        # if not completely out of position, go for a shot
        if (
            align(my_intercept.car.position, my_intercept.ball, their_goal) > 0
            or ground_distance(my_intercept, my_goal) > 6000
        ):
            return offense.any_shot(info, my_intercept.car, their_goal, my_intercept)

        # otherwise try to clear
        else:
            return defense.any_clear(info, my_intercept.car)

    # if I'm nearest to goal, stay far back
    if min(my_team, key=lambda car: distance(car, my_goal)) is my_car:
        return GeneralDefense(my_car, info, my_intercept.position, 7000)

    # otherwise get into position
    return GeneralDefense(my_car, info, my_intercept.position, 4000)
