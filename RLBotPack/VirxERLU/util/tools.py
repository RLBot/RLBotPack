from util.routines import Aerial, double_jump, ground_shot, jump_shot, virxrlcu
from util.utils import Vector, math, side, cap


def find_ground_shot(agent, target, cap_=6):
    return find_shot(agent, target, cap_, can_aerial=False, can_double_jump=False, can_jump=False)


def find_any_ground_shot(agent, cap_=6):
    return find_any_shot(agent, cap_, can_aerial=False, can_double_jump=False, can_jump=False)


def find_jump_shot(agent, target, cap_=6):
    return find_shot(agent, target, cap_, can_aerial=False, can_double_jump=False, can_ground=False)


def find_any_jump_shot(agent, cap_=6):
    return find_any_shot(agent, cap_, can_aerial=False, can_double_jump=False, can_ground=False)


def find_double_jump(agent, target, cap_=6):
    return find_shot(agent, target, cap_, can_aerial=False, can_jump=False, can_ground=False)


def find_any_double_jump(agent, cap_=6):
    return find_any_shot(agent, cap_, can_aerial=False, can_jump=False, can_ground=False)


def find_aerial(agent, target, cap_=6):
    return find_shot(agent, target, cap_, can_double_jump=False, can_jump=False, can_ground=False)


def find_any_aerial(agent, cap_=6):
    return find_any_shot(agent, cap_, can_double_jump=False, can_jump=False, can_ground=False)


def find_shot(agent, target, cap_=6, can_aerial=True, can_double_jump=True, can_jump=True, can_ground=True):
    if not can_aerial and not can_double_jump and not can_jump and not can_ground:
        agent.print("WARNING: All shots were disabled when find_shot was ran")
        return

    # Takes a tuple of (left,right) target pairs and finds routines that could hit the ball between those target pairs
    # Only meant for routines that require a defined intercept time/place in the future

    # Assemble data in a form that can be passed to C
    targets = (
        tuple(target[0]),
        tuple(target[1])
    )

    me = agent.me.get_raw(agent)

    game_info = (
        agent.boost_accel,
        agent.best_shot_value
    )

    gravity = tuple(agent.gravity)

    max_aerial_height = 1200 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
    min_aerial_height = 551 if max_aerial_height > 1200 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else (150 if agent.boost_amount == 'unlimited' or agent.me.airborne else 450)

    is_on_ground = not agent.me.airborne
    can_ground = is_on_ground and can_ground
    can_jump = is_on_ground and can_jump
    can_double_jump = is_on_ground and can_double_jump

    if not can_ground and not can_jump and not can_double_jump and not can_aerial:
        return

    # Here we get the slices that need to be searched - by defining a cap, we can reduce the number of slices and improve search times
    slices = get_slices(agent, cap_)

    if slices is None:
        return

    # Loop through the slices
    for ball_slice in slices:
        # Gather some data about the slice
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time - (1 / 120)

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212.75:
            return  # abandon search if ball is scored at/after this point

        ball_info = (ball_location, (ball_slice.physics.velocity.x, ball_slice.physics.velocity.y, ball_slice.physics.velocity.z))

        # Check if we can make a shot at this slice
        # This operation is very expensive, so we use C to improve run time
        shot = virxrlcu.parse_slice_for_shot_with_target(can_ground, can_jump, can_double_jump, can_aerial and (min_aerial_height < ball_location[2] < max_aerial_height), time_remaining, *game_info, gravity, ball_info, me, targets)

        if shot['found'] == 1:
            if shot['shot_type'] == 3:
                return Aerial(intercept_time, (Vector(*shot['targets'][0]), Vector(*shot['targets'][1])), shot['fast'])

            shot_switch = [
                ground_shot,
                jump_shot,
                double_jump
            ]
            return shot_switch[shot['shot_type']](intercept_time, (Vector(*shot['targets'][0]), Vector(*shot['targets'][1])))


def find_any_shot(agent, cap_=6, can_aerial=True, can_double_jump=True, can_jump=True, can_ground=True):
    if not can_aerial and not can_double_jump and not can_jump and not can_ground:
        agent.print("WARNING: All shots were disabled when find_any_shot was ran")
        return

    # Only meant for routines that require a defined intercept time/place in the future

    # Assemble data in a form that can be passed to C
    me = agent.me.get_raw(agent)

    game_info = (
        agent.boost_accel,
        agent.best_shot_value
    )

    gravity = tuple(agent.gravity)

    max_aerial_height = 1200 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
    min_aerial_height = 551 if max_aerial_height > 1200 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else (150 if agent.boost_amount == 'unlimited' or agent.me.airborne else 450)

    is_on_ground = not agent.me.airborne
    can_ground = is_on_ground and can_ground
    can_jump = is_on_ground and can_jump
    can_double_jump = is_on_ground and can_double_jump

    if not can_ground and not can_jump and not can_double_jump and not can_aerial:
        return

    # Here we get the slices that need to be searched - by defining a cap, we can reduce the number of slices and improve search times
    slices = get_slices(agent, cap_)

    if slices is None:
        return

    # Loop through the slices
    for ball_slice in slices:
        # Gather some data about the slice
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time - (1 / 120)

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212.75:
            return  # abandon search if ball is scored at/after this point

        ball_info = (ball_location, (ball_slice.physics.velocity.x, ball_slice.physics.velocity.y, ball_slice.physics.velocity.z))

        # Check if we can make a shot at this slice
        # This operation is very expensive, so we use C to improve run time
        shot = virxrlcu.parse_slice_for_shot(can_ground, can_jump, can_double_jump, can_aerial and (min_aerial_height < ball_location[2] < max_aerial_height), time_remaining, *game_info, gravity, ball_info, me)

        if shot['found'] == 1:
            if shot['shot_type'] == 3:
                return Aerial(intercept_time, fast_aerial=shot['fast'])

            shot_switch = [
                ground_shot,
                jump_shot,
                double_jump
            ]
            return shot_switch[shot['shot_type']](intercept_time)


def get_slices(agent, cap_):
    # Get the struct
    struct = agent.ball_prediction_struct

    # Make sure it isn't empty
    if struct is None:
        return

    start_slice = 12
    end_slices = None

    # If we're shooting, crop the struct
    if agent.shooting and agent.stack[0].__class__.__name__ != "short_shot":
        # Get the time remaining
        time_remaining = agent.stack[0].intercept_time - agent.time
        if time_remaining < 0.5 and time_remaining >= 0:
            return
            
        # if the shot is done but it's working on it's 'follow through', then ignore this stuff
        if time_remaining > 0:
            # Convert the time remaining into number of slices, and take off the minimum gain accepted from the time
            min_gain = 0.05
            end_slice = round(min(time_remaining - min_gain, cap_) * 60)

    if end_slices is None:
        # Cap the slices
        end_slice = round(cap_ * 60)

    # We can't end a slice index that's lower than the start index
    if end_slice <= start_slice:
        return

    # for every second worth of slices that we have to search, skip 1 more slice (for performance reasons) - min 1 and max 3
    skip = cap(end_slice - start_slice / 60, 1, 3)
    return struct.slices[start_slice:end_slice:skip]
