from typing import Optional

from settings import TURN_COOLDOWN
from turn import Turn
from utilities.rendering import draw_cross
from utilities.rlmath import argmax
from utilities.vec import Vec3, normalize, dot, norm


def about_to_score(bot) -> bool:
    bp = bot.get_ball_prediction_struct()
    STEP_SIZE = 5
    for i in range(0, bp.num_slices, STEP_SIZE):
        pos = Vec3(bp.slices[i].physics.location)
        if abs(pos.y) - 5120 > 80:
            return True
    else:
        return False


def drive_to(bot, target: Vec3) -> Turn:
    """
    Find the most naive turn to get to the target position
    """

    car = bot.info.my_car
    turns = Turn.all(car)

    # Find best turn
    delta_n = normalize(target - car.pos)
    turn, _ = argmax(turns, lambda turn: dot(turn.dir, delta_n))

    return turn


def smart_drive_to(bot, target: Vec3) -> Turn:
    """
    Find a turn that will get us to the target position and avoid creating short line segments
    """
    car = bot.info.my_car
    speed = min(2295, norm(car.vel) * 1.4)
    next_turn_pos = car.pos if bot.can_turn() else car.pos + car.forward * speed * bot.time_till_turn()
    line_seg_min_len = speed * TURN_COOLDOWN
    # local.x: how far in front of my car
    # local.y: how far to the left of my car
    # local.z: how far above my car
    delta_local = dot(target - next_turn_pos, car.rot)
    SOME_SMALL_VALUE = 20
    if delta_local.x < 0:
        delta_local.x = -delta_local.x
    if SOME_SMALL_VALUE < delta_local.x < line_seg_min_len:
        # Turning now results in a miss later
        return Turn.no_turn(car)
    else:
        return drive_to(bot, target)


def predict_time_of_arrival(bot, target: Vec3) -> float:
    """
    Returns a rough prediction of how long it will take to reach the target position
    """
    car = bot.info.my_car
    speed = min(2295, norm(car.vel) * 1.5)
    next_turn_pos = car.pos if bot.can_turn() else car.pos + car.forward * speed * bot.time_till_turn()
    delta_local = dot(target - next_turn_pos, car.rot)
    dist = abs(delta_local.x) + abs(delta_local.y) + abs(delta_local.z) - 20
    time = max(0, bot.time_till_turn()) + dist / speed
    # If ball is behind, we need turn twice, so we add an additional TURN_COOLDOWN
    time = time if dot(car.forward, target - next_turn_pos) >= 0 else time + TURN_COOLDOWN
    return time * 1.2  # Seems like we are still underestimating a bit, so we increase it a bit


def find_shot_target(bot) -> Optional[Vec3]:
    bp = bot.get_ball_prediction_struct()
    STEP_SIZE = 3
    STEP_DUR = 6 * STEP_SIZE / 360
    for i in range(0, bp.num_slices, STEP_SIZE):
        pos = Vec3(bp.slices[i].physics.location)
        # Offset a bit
        pos = pos + normalize(bot.info.opp_goal.pos - pos) * -50
        time = i * STEP_DUR
        if abs(predict_time_of_arrival(bot, pos) - time) < 0.1:
            return pos
    else:
        return None


def shoot_at_goal(bot) -> Optional[Turn]:
    target = find_shot_target(bot)
    if target is not None:
        draw_cross(bot, target, bot.renderer.team_color())
    return smart_drive_to(bot, target) if target is not None else None


def find_turn(bot) -> Optional[Turn]:
    if not about_to_score(bot):
        shot = shoot_at_goal(bot)
        if shot is not None:
            return shot
    mid = (bot.info.own_goal.front + bot.info.ball.pos) / 2
    return smart_drive_to(bot, mid)
