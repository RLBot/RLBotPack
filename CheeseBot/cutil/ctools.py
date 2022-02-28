from cutil.cutils import cap, closest_point, furthest_point, get_back_post_vector, align_goalposts
from objects import Vector3
from utils import post_correction, in_field, find_slope, side
from routines import jump_shot, aerial_shot
import math
from cutil.control_panel import *


#TODO: Replace repeated code in the various find_intercept functions with the parse_shot_for_intercept function.
#TODO: Standardize struct format for find_intercept functions. Right now they all return different things.
def determine_shot(agent, target_override = None, min_shot_speed = 0, max_shot_time = 3.0, offense_defense = 1):

    #gosling's hit finding algorithm is pretty good, but there's definitely room for improvement:
    #1. it exhaustively calculates every single possible shot at a target, even though bots typically only use the first one
    #2. it looks for shots at more than one target at a time. This does allow for "if shots are not available for this target, then use another target", but it tanks performance
    #3. it doesn't check if the approach vector is inside the field (but this can probably be changed)
    #4. it will sometimes return shots that are really, really slow (the original PotatOSBB needed a separate determine shot function to figure that out)

    #I think the plan with this is to wrap it in a determine_shot() function that decides the target location and what the minimum hit speed needs to be.
    #Then we call that every four ticks or so (or when the latest_touch var updates)

    slices = get_slices(agent, 6)

    if slices is None:
        return None

    else:
        for slice in slices:
            intercept_time = slice.game_seconds
            time_remaining = intercept_time - agent.time

            if time_remaining > 0:
                ball_location = Vector3(slice.physics.location)
                ball_velocity = Vector3(slice.physics.velocity).magnitude()

                if abs(ball_location[1]) > 5250:
                    return None #abandon search if ball scored after this point

                car_to_ball = ball_location - agent.me.location
                #Adding a True to a vector's normalize will have it also return the magnitude of the vector
                direction, distance = car_to_ball.normalize(True)


                #How far the car must turn in order to face the ball, for forward and reverse
                forward_angle = direction.angle(agent.me.forward)
                backward_angle = math.pi - forward_angle

                #Accounting for the average time it takes to turn and face the ball
                #Backward is slightly longer as typically the car is moving forward and takes time to slow down
                forward_time = time_remaining - (forward_angle * 0.318)
                backward_time = time_remaining - (backward_angle * 0.418)

                #If the car only had to drive in a straight line, we ensure it has enough time to reach the ball (a few assumptions are made)
                forward_flag = forward_time > 0.0 and (distance*1.025 / forward_time) < (2299 if agent.me.boost > distance/100 else max(1400, 0.8 * agent.me.velocity.flatten().magnitude()))
                backward_flag = distance < 1500 and backward_time > 0.0 and (distance*1.05 / backward_time) < 1200

                #Provided everything checks out, we begin to look at the target pairs
                if forward_flag or backward_flag:

                        min_shot_alignment = CTOOLS_DETERMINE_SHOT_MIN_SHOT_ALIGNMENT_DEFAULT
                        #target selection
                        if target_override is not None:
                            target = target_override
                        else:

                            if offense_defense == -1:
                                #panic defense mode
                                target = agent.anti_target
                                min_shot_alignment = -1
                            else:

                                if agent.ball_going_into_our_net or agent.ball_going_into_danger_zone or ((ball_location.y * side(agent.team)) > 4400):
                                    target = agent.anti_target
                                    min_shot_alignment = -1
                                elif (ball_location.y * side(agent.team)) > 4500:
                                    if ball_location.x * side(agent.team) < 0:
                                        target = agent.left_side_shot
                                    else:
                                        target = agent.right_side_shot
                                # elif ball_location.y * side(agent.team) < 3600 or not agent.closest_to_ball:
                                #     target = agent.foe_goal_shot
                                # else:
                                #     target = agent.upfield_shot
                                elif offense_defense == 0:
                                    target = agent.upfield_shot
                                else:
                                    target = agent.foe_goal_shot

                        shot_alignment = align_goalposts(agent.me.location, ball_location, target[0], target[1])

                        #First we correct the target coordinates to account for the ball's radius
                        #If fits == True, the ball can be scored between the target coordinates
                        left, right, fits = post_correction(ball_location, target[0], target[1])
                        if fits:
                            #Now we find the easiest direction to hit the ball in order to land it between the target points
                            left_vector = (left - ball_location).normalize()
                            right_vector = (right - ball_location).normalize()
                            best_shot_vector = direction.clamp(left_vector, right_vector)

                            #Check to make sure our approach is inside the field
                            if in_field(ball_location - (700*best_shot_vector),1):
                                #The slope represents how close the car is to the chosen vector, higher = better
                                #A slope of 1.0 would mean the car is 45 degrees off
                                considered_shots = []
                                slope = find_slope(best_shot_vector.flatten(),car_to_ball.flatten())
                                if forward_flag:
                                    if (ball_location[2] <= 300 or (not in_field(ball_location, 200) and not in_field(agent.me.location, 100))) and slope > 0.0 and shot_alignment > min_shot_alignment:
                                        considered_shots.append(jump_shot(ball_location,intercept_time,best_shot_vector,slope))
                                    if (ball_location[2] > 325 and slope > 1 and cap(ball_location[2]-400, 100, 2000) * 0.1 < agent.me.boost
                                            and abs((car_to_ball / forward_time) - agent.me.velocity).magnitude() - 300 < 400 * forward_time):
                                            considered_shots.append(aerial_shot(ball_location,intercept_time,best_shot_vector,slope))
                                # elif backward_flag and ball_location[2] <= 280 and slope > 0.25:
                                #     considered_shots.append(jump_shot(ball_location,intercept_time,best_shot_vector,slope,-1))

                                for considered_shot in considered_shots:
                                    #speed consideration - this way we don't have to go for really slow shots unless it's needed.
                                    #also integrating this into find_hit means that the bot can keep scanning the struct for possible shots if the first one isn't possible.
                                    shot_distance = (agent.me.location - considered_shot.ball_location).flatten().magnitude()
                                    shot_time = considered_shot.intercept_time - agent.time
                                    average_speed = shot_distance/shot_time
                                    if average_speed > min_shot_speed and considered_shot.intercept_time - agent.time < max_shot_time:
                                        return considered_shot



def get_slices(agent, cap_):
    #Virx did this, he's smarter than me
    # Get the struct
    struct = agent.get_ball_prediction_struct()

    # Make sure it isn't empty
    if struct is None:
        return

    start_slice = 6
    end_slices = None

    # If we're shooting, crop the struct
    if agent.shooting and hasattr(agent.stack[0], "intercept_time") and agent.stack[0].intercept_time is not None:
        # Get the time remaining
        time_remaining = agent.stack[0].intercept_time - agent.time
        if 0 < time_remaining < 0.5:
            return

        # if the shot is done but it's working on it's 'follow through', then ignore this stuff
        if time_remaining > 0:
            # Convert the time remaining into number of slices, and take off the minimum gain accepted from the time
            min_gain = 0.2
            end_slice = round(min(time_remaining - min_gain, cap_) * 60)

    #wait a sec something's not right here:
    #shouldn't this be an if-else statement? Because currently this is cropping the struct if a shot's occuring, then immediately uncropping it.

    if end_slices is None:
        # Cap the slices
        end_slice = round(cap_ * 60)

    # We can't end a slice index that's lower than the start index
    if end_slice <= start_slice:
        return

    # for every second worth of slices that we have to search, skip 1 more slice (for performance reasons) - min 1 and max 3
    skip = cap(end_slice - start_slice / 60, 1, 3)
    return struct.slices[start_slice:end_slice:skip]

def find_intercept_time(car, agent, ball_prediction_slices = None, return_intercept_location_too = False, time_limit: float = None, time_to_subtract = 0.0):
        #find the earliest time that a car can intercept the ball. Returns None otherwise.
        earliest_intercept_time = None
        earliest_intercept_location = None

        ball_prediction_struct = ball_prediction_slices if ball_prediction_slices is not None else get_slices(agent, 6)

        if ball_prediction_struct is not None:

            for slice in ball_prediction_slices:
                prediction_slice = slice
                intercept_time = prediction_slice.game_seconds
                time_remaining = intercept_time - agent.time - time_to_subtract

                if time_limit is not None:
                    if intercept_time - agent.time > time_limit:
                        break

                if time_remaining > 0:
                    current_prediction_slice_ball_location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)
                    time_to_reach_intercept = time_to_reach_location(car, current_prediction_slice_ball_location)
                    if time_to_reach_intercept < time_remaining:
                        earliest_intercept_time = intercept_time
                        earliest_intercept_location = current_prediction_slice_ball_location
                        #print("Time to run non np code: " + str(toc - tic))
                        if return_intercept_location_too:
                            return earliest_intercept_time, earliest_intercept_location
                        else:
                            return earliest_intercept_time

        #print("Time to run non np code: " + str(toc - tic))
        if return_intercept_location_too:
            return None, None
        else:
            return None

def find_earliest_good_intercept_time(car, agent, ball_prediction_slices = None, return_intercept_location_too = False, min_align_limit = 0.0):
    ball_prediction_struct = ball_prediction_slices if ball_prediction_slices is not None else get_slices(agent, 6)

    #print(ball_prediction_struct)

    if ball_prediction_struct is not None:
        for slice in ball_prediction_struct:
            prediction_slice = slice
            intercept_time = prediction_slice.game_seconds
            time_remaining = intercept_time - agent.time

            if time_remaining > 0:
                current_prediction_slice_ball_location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)
                if align_goalposts(car.location, current_prediction_slice_ball_location, agent.foe_goal.left_post, agent.foe_goal.right_post) > min_align_limit:
                    time_to_reach_intercept = time_to_reach_location(car, current_prediction_slice_ball_location)
                    if time_to_reach_intercept < time_remaining:
                        earliest_intercept_time = intercept_time
                        earliest_intercept_location = current_prediction_slice_ball_location
                    #print("Time to run non np code: " + str(toc - tic))
                        if return_intercept_location_too:
                            return earliest_intercept_time, earliest_intercept_location
                        else:
                            return earliest_intercept_time

        #print("Time to run non np code: " + str(toc - tic))
        if return_intercept_location_too:
            return None, None
        else:
            return None


def find_intercept_time_with_detour(car, agent, ball_prediction_slices = None, return_intercept_location_too = False, time_limit: float = None, time_to_subtract = 0.0, ball_height_max = 9999):
    #find the earliest time that a car can intercept the ball. Returns None otherwise.
    earliest_intercept_time = None
    earliest_intercept_location = None

    ball_prediction_struct = ball_prediction_slices if ball_prediction_slices is not None else get_slices(agent, 6)

    if ball_prediction_struct is not None:

        for slice in ball_prediction_slices:
            prediction_slice = slice
            intercept_time = prediction_slice.game_seconds
            time_remaining = intercept_time - agent.time - time_to_subtract

            if time_limit is not None:
                if intercept_time - agent.time > time_limit:
                    break

            if time_remaining > 0:
                current_prediction_slice_ball_location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)
                reposition_target = find_reposition_target(agent, current_prediction_slice_ball_location)
                time_to_reach_intercept = time_to_reach_multiple_locations(car, [reposition_target, current_prediction_slice_ball_location])
                if time_to_reach_intercept < time_remaining:
                    earliest_intercept_time = intercept_time
                    earliest_intercept_location = current_prediction_slice_ball_location
                    #print("Time to run non np code: " + str(toc - tic))
                    if return_intercept_location_too:
                        return earliest_intercept_time, earliest_intercept_location
                    else:
                        return earliest_intercept_time

    #print("Time to run non np code: " + str(toc - tic))
    if return_intercept_location_too:
        return None, None
    else:
        return None

def find_reposition_target(agent, intercept_vector_location, desired_distance = 3000):
    my_goal_to_ball = (intercept_vector_location - agent.friend_goal.location).flatten().normalize()
    car_to_ball, car_to_ball_distance = (intercept_vector_location - agent.me.location).flatten().normalize(True)
    ball_to_goal_magnitude = (intercept_vector_location - agent.friend_goal.location).flatten().magnitude()

    reposition_target = intercept_vector_location.flatten() + Vector3(0, -my_goal_to_ball.y, 0) * min(desired_distance, ball_to_goal_magnitude - 150)
    final_target = reposition_target
    # # print("Intercept location: " + str(intercept_vector_location))
    # # print("Reposition target: " + str(reposition_target))
    # reposition_target.x = cap(reposition_target.x, -3796, 3796)
    # reposition_target.y = cap(reposition_target.y, -5120, 5120)
    #
    # near_goal = abs(agent.me.location[1] - agent.friend_goal.location[1]) < 3000
    # side_shift = 400 if near_goal else 1800
    # points = [reposition_target + Vector3(side_shift, 0, 0), reposition_target - Vector3(side_shift, 0, 0)]
    # #print("Points: " + str(points))
    # final_target = closest_point(reposition_target, points) if near_goal else furthest_point(reposition_target, points)
    # if abs(intercept_vector_location[0]) < 1000 or car_to_ball_distance < 1000:
    #     final_target = closest_point(agent.me.location, points)
    # #print("Final Target: " + str(final_target))

    if abs(final_target.y) > 4500:
        final_target = get_back_post_vector(agent, intercept_vector_location)
    else:
        final_target.x = cap(final_target.x, -3400, 3400)
        final_target.y = cap(final_target.y, -4500, 4500)

    return final_target


def time_to_reach_location(car, target_location):
    #If I was doing this in numpy:
    #car to target and direction need to not be in an array. Forward angle, backward angle, and distance need not be.
    car_to_target = (target_location - car.location).flatten()
    direction = car_to_target.normalize(False)
    distance = car_to_target.magnitude()

    forward_angle = direction.angle(car.forward)
    backward_angle = math.pi  - forward_angle

    forward_time_to_turn_around = forward_angle * 0.318
    forward_time_to_drive_straight_there = distance*1.025 / (2299 if car.boost > distance/100 else max(1400.0, 0.8, car.velocity.flatten().magnitude()))

    backward_angle_time_to_turn_around = backward_angle * 0.418
    backward_time_to_drive_straight_there = distance * 1.025 / 1200

    forward_total_time = forward_time_to_turn_around + forward_time_to_drive_straight_there
    backward_total_time = backward_angle_time_to_turn_around + backward_time_to_drive_straight_there

    total_time = min(forward_total_time, backward_total_time)
    #print("Time to run time_to_reach_location: " + str(toc - tic))
    return total_time

def time_to_reach_multiple_locations(car, targets):
    #we're making a big assumption here: this is modeled as driving straight to the point, then theoretically steering on a dime. Anything else is when things become a bit more complicated
    #find the total distance between all of the points, as well as the total steering required
    #create a list that's got some vectors in it. Start with the car's initial location to the first point, then the first point to the second point, and so on.
    #then add up the total angle between each vector and the magnitude of each vector. This should give the total distance and the total steering angle.

    vector_list = []
    car_to_first_target = (targets[0] - car.location).flatten()
    vector_list.append(car_to_first_target)

    for count, value in enumerate(targets):
        if count + 1 <= len(targets) - 1:
            vector = (targets[count+1] - value).flatten()
            vector_list.append(vector)

    total_distance = 0.0
    total_steering_angle = 0.0

    #once we have this list, start finding magnitudes.
    #for each vector in the list, get its magnitude and then add it to total_distance
    #if the vector is not the last vector in the list, take the angle between the current vector and the next one. Then add that to total steering angle.


    for count, value in enumerate(vector_list):
        total_distance += value.magnitude()
        if count < len(vector_list) - 1:
            # normalize both vectors
            current_vector_direction = value.normalize(False)
            next_vector_direction = vector_list[count + 1].normalize(False)
            steering_angle = current_vector_direction.angle(next_vector_direction)
            total_steering_angle += steering_angle

    total_time_to_steer = total_steering_angle * 0.318
    total_time_to_drive_straight_there = total_distance*1.025 / (2299 if car.boost > total_distance/100 else max(1400.0, 0.8, car.velocity.flatten().magnitude()))
    total_time = total_time_to_steer + total_time_to_drive_straight_there
    return total_time

def ball_going_into_our_net(agent):
    #left post and right post are as you're looking at it when you're facing the goal
    ball_prediction = agent.get_ball_prediction_struct()

    slices = get_slices(agent, 6)

    if slices is not None:
        for slice in slices:
            prediction_slice = slice
            ball_location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)


            if -side(agent.team) * ball_location.y < -5200:
                return True

    return False

def ball_going_into_danger_zone(agent):
    slices = get_slices(agent, 6)
    if slices is not None:
        for slice in slices:
            ball_location = Vector3(slice.physics.location)

            if -side(agent.team) * ball_location.y < -3600 and -1600 < ball_location.x < 1600:
                return True

    return False

def ball_going_into_their_danger_zone(agent):
    slices = get_slices(agent, 6)
    if slices is not None:
        for slice in slices:
            ball_location = Vector3(slice.physics.location)

            if side(agent.team) * ball_location.y < -3600 and -1600 < ball_location.x < 1600:
                return True

    return False

def check_if_closest_to_goal(agent):
    closest_to_goal = True
    my_distance_to_goal = (agent.me.location - agent.friend_goal.location).flatten().magnitude()

    for car in agent.friends:
        their_distance_to_goal = (car.location - agent.friend_goal.location).flatten().magnitude()
        if their_distance_to_goal < my_distance_to_goal:
            closest_to_goal = False

    return closest_to_goal

def parse_slice_for_intercept(agent, prediction_slice, car, foe_goalposts, time_to_subtract= 0.0):
    return_struct = None
    intercept_time = prediction_slice.game_seconds
    time_remaining = intercept_time - agent.time - time_to_subtract

    current_prediction_slice_ball_location = Vector3(prediction_slice.physics.location.x, prediction_slice.physics.location.y, prediction_slice.physics.location.z)
    time_to_reach_intercept = time_to_reach_location(car, current_prediction_slice_ball_location)
    if time_to_reach_intercept < time_remaining:
        #Considering that we need to calculate
        intercept_time = intercept_time
        intercept_location = current_prediction_slice_ball_location
        intercept_alignment = align_goalposts(car.location, current_prediction_slice_ball_location, foe_goalposts.left_post, foe_goalposts.right_post)
        intercept_current_car_velocity = car.velocity.flatten().normalize()
        car_to_intercept = (intercept_location - car.location).flatten().normalize()
        angle_between_car_velocity_and_car_to_intercept = car_to_intercept.angle(intercept_current_car_velocity)

        return_struct = {"time": intercept_time, "location": intercept_location, "alignment": intercept_alignment, "velocity_angle":angle_between_car_velocity_and_car_to_intercept}

    return return_struct


def find_earliest_intercept_test(agent, car, ball_prediction, time_limit, foe_goalposts, only_accept_good_intercepts=False, time_to_subtract=0.0):
    ball_prediction = get_slices(agent, 6) if ball_prediction is None else ball_prediction

    earliest_intercept = None
    if ball_prediction is not None:
        for slice in ball_prediction:
            if time_limit is not None:
                if slice.time > time_limit:
                    break
            intercept_struct = parse_slice_for_intercept(agent, slice, car, foe_goalposts)
            if intercept_struct is not None:
                if intercept_struct["alignment"] > 0.2:
                    earliest_intercept = intercept_struct
                    break
                elif earliest_intercept is None and not only_accept_good_intercepts:
                    earliest_intercept = intercept_struct
                    if time_limit is None:
                        time_limit = intercept_struct["time"] + 1.5
                        only_accept_good_intercepts = True

    return earliest_intercept

def ones_defense_offense_switch_test(agent):
    #returns 1 if the bot should go on offense, 0 if it should go on defense, and -1 if it should go on panic defence.
    my_align = align_goalposts(agent.me.location, agent.ball.location, agent.foe_goal.left_post, agent.foe_goal.right_post)
    foe_align = align_goalposts(agent.foes[0].location, agent.ball.location, agent.friend_goal.left_post, agent.friend_goal.right_post)
    my_distance_to_ball = (agent.me.location - agent.ball.location).magnitude()
    foe_distance_to_ball = (agent.foes[0].location - agent.ball.location).magnitude()

    if my_align > 0.0 and foe_align < 0.0:
        if my_distance_to_ball < foe_distance_to_ball or ball_going_into_their_danger_zone(agent):
            return 2
        else:
            return 1
    elif my_align < 0.0 and foe_align > 0.0:
        return -1
    elif my_align > 0.0 and foe_align < 0.0:
        if agent.ball_location.y * side(agent.team) > 3600:
            return 0
        elif my_distance_to_ball * 3.1 < foe_distance_to_ball or ball_going_into_their_danger_zone(agent):
            return 2
        elif my_distance_to_ball * 1.5 < foe_distance_to_ball:
            return 1
        else:
            return 0
    return -1





