import virxrlcu
from util.routines import Aerial, jump_shot, double_jump
from util.utils import Vector, math


def find_jump_shot(agent, target, weight=None, cap_=6):
    # Takes a tuple of (left,right) target pairs and finds routines that could hit the ball between those target pairs
    # Only meant for routines that require a defined intercept time/place in the future
    # Here we get the slices that need to be searched - by defining a cap or a weight, we can reduce the number of slices and improve search times
    slices = get_slices(agent, cap_, weight=weight)

    if slices is None:
        return

    # Assemble data in a form that can be passed to C
    target = (
        target[0].tuple(),
        target[1].tuple()
    )

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    # Loop through the slices
    for ball_slice in slices:
        # Gather some data about the slice
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            continue

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return  # abandon search if ball is scored at/after this point

        # If the ball is above what this function can handle, don't bother with any further processing and skip to the next slice
        if ball_location[2] > 300:
            continue

        # Check if we can make a shot at this slice
        # This operation is very expensive, so we use a custom C function to improve run time
        shot = virxrlcu.parse_slice_for_jump_shot_with_target(time_remaining, agent.best_shot_value, ball_location, *me, *target, cap_)

        # If we found a viable shot, pass the data into the shot routine and return the shot
        if shot['found'] == 1:
            return jump_shot(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)


def find_any_jump_shot(agent, cap_=3):
    slices = get_slices(agent, cap_)

    if slices is None:
        return

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            continue

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if ball_location[2] > 300:
            continue

        shot = virxrlcu.parse_slice_for_jump_shot(time_remaining, agent.best_shot_value, ball_location, *me, cap_)

        if shot['found'] == 1:
            return jump_shot(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)


def find_double_jump(agent, target, weight=None, cap_=6):
    slices = get_slices(agent, cap_, weight=weight, start_slice=30)

    if slices is None:
        return

    target = (
        target[0].tuple(),
        target[1].tuple()
    )

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time - 0.3

        if time_remaining <= 0:
            continue

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if ball_location[2] > 490 or ball_location[2] < 300:
            continue

        shot = virxrlcu.parse_slice_for_double_jump_with_target(time_remaining, agent.best_shot_value, ball_location, *me, *target, cap_)

        if shot['found'] == 1:
            return double_jump(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)


def find_any_double_jump(agent, cap_=3):
    slices = get_slices(agent, cap_, start_slice=30)

    if slices is None:
        return

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time - 0.3

        if time_remaining <= 0:
            continue

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if ball_location[2] > 490 or ball_location[2] < 300:
            continue

        shot = virxrlcu.parse_slice_for_double_jump(time_remaining, agent.best_shot_value, ball_location, *me, cap_)

        if shot['found'] == 1:
            return double_jump(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)


def find_aerial(agent, target, weight=None, cap_=6):
    slices = get_slices(agent, cap_, weight=weight)

    if slices is None:
        return

    target = (
        target[0].tuple(),
        target[1].tuple()
    )

    me = (
        agent.me.location.tuple(),
        agent.me.velocity.tuple(),
        agent.me.up.tuple(),
        agent.me.forward.tuple(),
        1 if agent.me.airborne else -1,
        agent.me.boost
    )

    gravity = agent.gravity.tuple()

    max_aerial_height = 643 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
    min_aerial_height = 643 if max_aerial_height > 643 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else 500

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if min_aerial_height > ball_location[2] or ball_location[2] > max_aerial_height:
            continue

        shot = virxrlcu.parse_slice_for_aerial_shot_with_target(time_remaining, agent.best_shot_value, agent.boost_accel, gravity, ball_location, me, *target, cap_)

        if shot['found'] == 1:
            return Aerial(Vector(*ball_location), Vector(*shot['ball_intercept']), intercept_time)


def find_any_aerial(agent, cap_=3):
    slices = get_slices(agent, cap_)

    if slices is None:
        return

    me = (
        agent.me.location.tuple(),
        agent.me.velocity.tuple(),
        agent.me.up.tuple(),
        agent.me.forward.tuple(),
        1 if agent.me.airborne else -1,
        agent.me.boost
    )

    gravity = agent.gravity.tuple()

    max_aerial_height = 735 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
    min_aerial_height = 551 if max_aerial_height > 643 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else 500

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if min_aerial_height > ball_location[2] or ball_location[2] > max_aerial_height:
            continue

        shot = virxrlcu.parse_slice_for_aerial_shot(time_remaining, agent.best_shot_value, agent.boost_accel, gravity, ball_location, me, cap_)

        if shot['found'] == 1:
            return Aerial(Vector(*ball_location), Vector(*shot['ball_intercept']), intercept_time)


def find_shot(agent, target, weight=None, cap_=6, can_aerial=True, can_double_jump=True, can_jump=True):
    if not can_aerial and not can_double_jump and not can_jump:
        agent.print("WARNING: All shots were disabled when find_shot was ran")
        return

    slices = get_slices(agent, cap_, weight=weight)

    if slices is None:
        return

    target = (
        target[0].tuple(),
        target[1].tuple()
    )

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    if can_aerial:
        me_a = (
            me[0],
            me[1],
            agent.me.up.tuple(),
            agent.me.forward.tuple(),
            1 if agent.me.airborne else -1,
            me[2]
        )

        gravity = agent.gravity.tuple()

        max_aerial_height = 643 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
        min_aerial_height = 643 if max_aerial_height > 643 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else 500

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if can_jump and not (ball_location[2] > 300):
            shot = virxrlcu.parse_slice_for_jump_shot_with_target(time_remaining, agent.best_shot_value, ball_location, *me, *target, cap_)

            if shot['found'] == 1:
                return jump_shot(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)
        
        if can_double_jump and not (ball_location[2] > 490 or ball_location[2] < 300):
            shot = virxrlcu.parse_slice_for_double_jump_with_target(time_remaining, agent.best_shot_value, ball_location, *me, *target, cap_)

            if shot['found'] == 1:
                return double_jump(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)

        if can_aerial and not (min_aerial_height > ball_location[2] or ball_location[2] > max_aerial_height):
            shot = virxrlcu.parse_slice_for_aerial_shot_with_target(time_remaining, agent.best_shot_value, agent.boost_accel, gravity, ball_location, me_a, *target, cap_)

            if shot['found'] == 1:
                return Aerial(Vector(*ball_location), Vector(*shot['ball_intercept']), intercept_time)


def find_any_shot(agent, cap_=3, can_aerial=True, can_double_jump=True, can_jump=True):
    if not can_aerial and not can_double_jump and not can_jump:
        agent.print("WARNING: All shots were disabled when find_shot was ran")
        return

    slices = get_slices(agent, cap_)

    if slices is None:
        return

    me = (
        agent.me.location.tuple(),
        agent.me.forward.tuple(),
        agent.me.boost
    )

    if can_aerial:
        me_a = (
            me[0],
            me[1],
            agent.me.up.tuple(),
            agent.me.forward.tuple(),
            1 if agent.me.airborne else -1,
            me[2]
        )

        gravity = agent.gravity.tuple()

        max_aerial_height = 643 if len(agent.friends) == 0 and len(agent.foes) == 1 else math.inf
        min_aerial_height = 643 if max_aerial_height > 643 and agent.me.location.z >= 2044 - agent.me.hitbox.height * 1.1 else 500

    for ball_slice in slices:
        intercept_time = ball_slice.game_seconds
        time_remaining = intercept_time - agent.time

        if time_remaining <= 0:
            return

        ball_location = (ball_slice.physics.location.x, ball_slice.physics.location.y, ball_slice.physics.location.z)

        if abs(ball_location[1]) > 5212:
            return

        if can_jump and not (ball_location[2] > 300):
            shot = virxrlcu.parse_slice_for_jump_shot(time_remaining, agent.best_shot_value, ball_location, *me, cap_)

            if shot['found'] == 1:
                return jump_shot(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)
        
        if can_double_jump and not (ball_location[2] > 490 or ball_location[2] < 300):
            shot = virxrlcu.parse_slice_for_double_jump(time_remaining, agent.best_shot_value, ball_location, *me, cap_)

            if shot['found'] == 1:
                return double_jump(Vector(*ball_location), intercept_time, Vector(*shot['best_shot_vector']), agent.best_shot_value)

        if can_aerial and not (min_aerial_height > ball_location[2] or ball_location[2] > max_aerial_height):
            shot = virxrlcu.parse_slice_for_aerial_shot(time_remaining, agent.best_shot_value, agent.boost_accel, gravity, ball_location, me_a, cap_)

            if shot['found'] == 1:
                return Aerial(Vector(*ball_location), Vector(*shot['ball_intercept']), intercept_time)


def get_slices(agent, cap_, weight=None, start_slice=12):
    # Get the struct
    struct = agent.predictions['ball_struct']

    # Make sure it isn't empty
    if struct is None:
        return

    # If we're shooting, crop the struct
    if agent.shooting:
        # Get the time remaining
        time_remaining = agent.stack[0].intercept_time - agent.time

        # Convert the time remaining into number of slices, and take off the minimum gain accepted from the time
        min_gain = 0.05 if weight is None or weight is agent.shot_weight else (agent.max_shot_weight - agent.shot_weight + 1) / 3
        end_slice = min(math.ceil((time_remaining - min_gain) * 60), math.ceil(cap_ * 60))

        # We can't end a slice index that's lower than the start index
        if end_slice <= 12:
            return

        # Half the time, double the slices
        if time_remaining <= 3:
            return struct.slices[start_slice:end_slice]

        return struct.slices[start_slice:end_slice:2]

    # If we're not shooting, then cap the slices at the cap
    end_slice = math.ceil(cap_ * 60)

    # Start 0.2 seconds in, and skip every other data point
    return struct.slices[start_slice:end_slice:2]
