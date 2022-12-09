from util.mechanics import *
from util.utils import *
import math
import numpy as np
from tmcp import TMCPHandler, TMCPMessage, ActionType

#This file is for small utilities for math and movement

def find_shots(agent, targets, extra_time):
    #find_hits looks into the future and finds all future hits that the car can reach in time
    #and that could be shot between the targets provided
    hits = {name:None for name in targets}
    ball_prediction = agent.get_ball_prediction_struct()
    for coarse_index in range(20, ball_prediction.num_slices, 20):
        if test_shot(agent, targets, ball_prediction.slices[coarse_index], hits, extra_time) == "scored":
            break
        if test_shot(agent, targets, ball_prediction.slices[coarse_index], hits, extra_time) != hits:
            for index in range(max(20, coarse_index - 20), coarse_index):
                if test_hit(agent, targets, ball_prediction.slices[index], hits) == "scored":
                    break
                if test_shot(agent, targets, ball_prediction.slices[index], hits, extra_time) != hits:
                    hits = test_shot(agent, targets, ball_prediction.slices[index], hits, extra_time)
    return hits

def test_shot(agent, targets, selected_slice, hits, extra_time):
    #Gather some data about the slice
    intercept_time = selected_slice.game_seconds
    time_remaining = intercept_time - agent.time
    if time_remaining > 0:
        ball_location = Vector3(selected_slice.physics.location)
        ball_velocity = Vector3(selected_slice.physics.velocity)

        if abs(ball_location[1]) > 5250:
            return "scored"

        car_to_ball = ball_location - agent.me.location

        wall_distance, towards_wall = distance_to_wall(ball_location)

        if is_on_wall(ball_location, True) and abs(ball_location[0]) > 1000:
            if is_on_wall(agent.me):
                distance = car_to_ball.magnitude()
                direction = car_to_ball.normalize()
            else:
                distance = ((ball_location.flatten() + towards_wall * (ball_location[2] + wall_distance - 100)) - agent.me.location).flatten().magnitude()
                direction = ((ball_location.flatten() + towards_wall * (ball_location[2] + wall_distance - 100)) - agent.me.location).normalize()
        else:
            distance = car_to_ball.flatten().magnitude()
            direction = car_to_ball.normalize()

        estimated_time = eta(agent.me, ball_location, direction, distance)
        time_to_jump = find_jump_time(cap(ball_location[2] - agent.me.location[2], 1, 500), ball_location[2] > 300)

        if estimated_time < time_remaining or ball_location.z > 640 or agent.me.airborne:
            for pair in targets:
                if hits[pair] != None:
                    continue
                #First we correct the target coordinates to account for the ball's radius
                #If swapped == True, the shot isn't possible because the ball wouldn't fit between the targets
                left, right, swapped = post_correction(ball_location, targets[pair][0], targets[pair][1])
                if not swapped:
                    #Now we find the easiest direction to hit the ball in order to land it between the target points
                    left_vector = (left - ball_location)
                    right_vector = (right - ball_location)
                    shot_vector = direction.clamp(left_vector, right_vector).normalize()

                    car_final_vel = car_to_ball / time_remaining
                    angle_turned = cap(distance / (500 + 800 / (2 - cap(extra_time, 0, 1))), 0, car_final_vel.angle3D(shot_vector))
                    
                    dodge_shot_speed = ball_velocity.magnitude() * 1.5 + cap(math.cos(car_final_vel.angle3D(shot_vector) - angle_turned) * car_final_vel.magnitude(), 0, car_final_vel.magnitude() * 1.5) + 500
                    ball_to_targets = (targets[pair][0] + targets[pair][1]) / 2 - ball_location

                    dodge_shot_angle = find_shot_angle(dodge_shot_speed, ball_to_targets.flatten().magnitude(), ball_to_targets.z)
                    dodge_max_angle = get_max_angle(cap(time_to_jump, 0.001, 1.5), abs(dodge_shot_angle) + 0.5, 11, 0.001)
                    dodge_shot_angle = cap(dodge_shot_angle, -dodge_max_angle, dodge_max_angle)

                    dodge_shot_vector = shot_vector.flatten().normalize() * math.cos(dodge_shot_angle) + Vector3(0,0,1) * math.sin(dodge_shot_angle)
                    dodge_shot_vector = (dodge_shot_vector * dodge_shot_speed - ball_velocity).normalize()
                    
                    norm_shot_speed = ball_velocity.magnitude() * 2 + 1

                    norm_shot_angle = find_shot_angle(norm_shot_speed, ball_to_targets.flatten().magnitude(), ball_to_targets.z)

                    norm_shot_vector = shot_vector.flatten().normalize() * math.cos(norm_shot_angle) + Vector3(0,0,1) * math.sin(norm_shot_angle)
                    norm_shot_vector = (norm_shot_vector * norm_shot_speed - ball_velocity).normalize()

                    flattened = ball_location.z - norm_shot_vector.z * 170 < 70
                
                    #Check to make sure our approach is inside the field
                    if in_field(ball_location - (100*shot_vector), 1):
                        #The slope represents how close the car is to the chosen vector, higher = better
                        #A slope of 1.0 would mean the car is 45 degrees off
                        slope = find_slope(shot_vector, car_to_ball)
                        if is_on_wall(ball_location, not is_on_wall(agent.me.location, False)) and abs(ball_location[0]) > 1000 and not agent.me.airborne:
                            hits[pair] = wall_hit(ball_location, intercept_time, dodge_shot_vector, 1, extra_time)
                        elif ball_location[2] < 120 and flattened and not agent.me.airborne:
                            hits[pair] = pop_up(ball_location, intercept_time, norm_shot_vector, 1, extra_time)
                        elif ball_location[2] - dodge_shot_vector[2] * 120 < 260 and not agent.me.airborne:
                            hits[pair] = shoot(ball_location, intercept_time, dodge_shot_vector, 1, extra_time)
                        elif 360 < ball_location[2] -norm_shot_vector[2] * 150 < 520 and not agent.me.airborne:
                            hits[pair] = double_jump(ball_location, intercept_time, norm_shot_vector, 1, extra_time)
                        elif ball_location[2] -norm_shot_vector[2] * 150 > 520:
                            aerial_attempt = aerial(ball_location, intercept_time, norm_shot_vector, 1)
                            if aerial_attempt.is_viable(agent, agent.time):
                                hits[pair] = aerial_attempt
    return hits

def find_next_hit(agent, cars):
    # goes through ball perdiction, and finds the soonest moment each car could possibly get to the ball
    # sets each cars next_hit fields to the moment in time it could get to soonest
    ball_prediction = agent.get_ball_prediction_struct()
    for coarse_index in range(20, ball_prediction.num_slices, 20):
        for car in cars:
            if test_hit(agent, car, ball_prediction.slices[coarse_index]):
                for index in range(max(20, coarse_index - 20), coarse_index):
                    if test_hit(agent, car, ball_prediction.slices[index]) == "scored":
                        return None
                    if test_hit(agent, car, ball_prediction.slices[index]):
                        return ball_moment(Vector3(ball_prediction.slices[index].physics.location), Vector3(ball_prediction.slices[index].physics.velocity), ball_prediction.slices[index].game_seconds)
    return None

def test_hit(agent, car, selected_slice, return_eta=False):
    #Gather some data about the slice
    intercept_time = selected_slice.game_seconds
    time_remaining = intercept_time - agent.time
    if time_remaining > 0:
        ball_location = Vector3(selected_slice.physics.location)
        ball_velocity = Vector3(selected_slice.physics.velocity)

        if abs(ball_location[1]) > 5250:
            return "scored"

        car_to_ball = ball_location - car.location

        wall_distance, towards_wall = distance_to_wall(ball_location)

        # gathers some info on the car relative to the slice
        if is_on_wall(ball_location, True) and abs(ball_location[0]) > 1000:
            if is_on_wall(car.location, False):
                distance = car_to_ball.magnitude()
                direction = car_to_ball.normalize()
            else:
                distance = ((ball_location.flatten() + towards_wall * (ball_location[2] + wall_distance - 100)) - car.location).flatten().magnitude()
                direction = ((ball_location.flatten() + towards_wall * (ball_location[2] + wall_distance - 100)) - car.location).normalize()
        else:
            distance = car_to_ball.flatten().magnitude()
            direction = car_to_ball.normalize()

        ground_shot = ball_location[2] < 500 or (is_on_wall(ball_location, True) and abs(ball_location[0]) > 1000)
        estimated_time = eta(car, ball_location, direction, distance)

        # can the car make it in time?
        if estimated_time < time_remaining:
            # if an aerial is needed, check if it can make it
            if not ground_shot:
                aerial_attempt = aerial(ball_location, intercept_time, car.forward, 1)
                if not aerial_attempt.is_viable(agent, agent.time):
                    return False
            # sets the next_hit field on the car
            if return_eta:
                return True, estimated_time
            return True
        return False
    else:
        return False

def attack(agent, extra_time=0.0):
    # ball_to_me = agent.ball.location - agent.me.location
    # targets = {"goal":(agent.foe_goal.left_post - Vector3(0, 0, 300), agent.foe_goal.right_post + Vector3(0, 0, 300))}
    # shots = find_hits(agent, targets)
    # if len(shots["goal"]) > 0:
    #     agent.push(shots["goal"][0])
    # else:
    #     agent.push(short_shot(agent.foe_goal.location))
    if len(agent.stack) < 1:
        ball_to_me = agent.ball.location - agent.me.location
        upfield_left = Vector3(-side(agent.team) * 2500, agent.ball.location.y - side(agent.team) * 2000, 500)
        midleft = Vector3(0, cap(agent.ball.location.y - side(agent.team) * 2000, 4000, -4000), 500)
        midright = Vector3(0, cap(agent.ball.location.y - side(agent.team) * 2000, 4000, -4000), 500)
        upfield_right = Vector3(side(agent.team) * 2500, agent.ball.location.y - side(agent.team) * 2000, 500)
        targets = {"goal":(agent.foe_goal.left_post, agent.foe_goal.right_post), "left":(upfield_left, midleft), "right":(midright, upfield_right)}
        shots = find_shots(agent, targets, extra_time)

        if shots["goal"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["goal"], aerial))) and (shots["left"] == None or shots["goal"].intercept_time - 0.2 < shots["left"].intercept_time):
            agent.push(shots["goal"])
            agent.me.intercept = shots["goal"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["goal"].shot_vector)
        elif shots["left"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["left"], aerial))) and sign(shots["left"].ball_location.x) == side(agent.team):
            agent.push(shots["left"])
            agent.me.intercept = shots["left"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["left"].shot_vector)
        elif shots["right"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["right"], aerial))) and sign(shots["right"].ball_location.x) == -side(agent.team):
            agent.push(shots["right"])
            agent.me.intercept = shots["right"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["right"].shot_vector)
        elif agent.me.airborne:
            agent.push(recovery())
            agent.plan = TMCPMessage.ready_action(agent.team, agent.index, -1.0)
        else:
            agent.push(short_shot(agent.foe_goal.location))
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept)
    elif isinstance(agent.stack[-1], goto):
        agent.pop()

def save(agent, extra_time=0.0):
    if len(agent.stack) < 1:
    # ball_to_me = agent.ball.location - agent.me.location
    # upfield_left = Vector3(-side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 2000, 0)
    # upfield_right = Vector3(side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 2000, 1000)
    # targets = {"goal":(agent.foe_goal.left_post - Vector3(0, 0, 300), agent.foe_goal.right_post + Vector3(0, 0, 300)), "upfield":(upfield_left, upfield_right)}
    # shots = find_hits(agent, targets)
    # if len(shots["upfield"]) > 0:
    #     agent.push(shots["upfield"][0])
    # elif len(shots["goal"]) > 0:
    #     agent.push(shots["goal"][0])
    # else:
    #     agent.push(short_shot(agent.foe_goal.location))

        ball_to_me = agent.ball.location - agent.me.location
        upfield_left = Vector3(-side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 3000, 0)
        midleft = Vector3(-side(agent.team) * 1500, agent.ball.location.y - side(agent.team) * 3000, 0)
        midright = Vector3(side(agent.team) * 1500, agent.ball.location.y - side(agent.team) * 3000, 0)
        upfield_right = Vector3(side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 3000, 1000)
        targets = {"goal":(agent.foe_goal.left_post, agent.foe_goal.right_post), "left":(upfield_left, midleft), "right":(midright, upfield_right)}
        shots = find_shots(agent, targets, extra_time)
        if shots["goal"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["goal"], aerial))) and abs(agent.ball.location.y) < 2000 and (shots["left"] == None or shots["goal"].intercept_time - 0.2 < shots["left"].intercept_time):
            agent.push(shots["goal"])
            agent.me.intercept = shots["goal"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["goal"].shot_vector)
        elif shots["left"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["left"], aerial))) and sign(shots["left"].ball_location.x) == -side(agent.team):
            agent.push(shots["left"])
            agent.me.intercept = shots["left"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["left"].shot_vector)
        elif shots["right"] != None and (not agent.me.airborne or (agent.me.airborne and isinstance(shots["right"], aerial))) and sign(shots["right"].ball_location.x) == side(agent.team):
            agent.push(shots["right"])
            agent.me.intercept = shots["right"].intercept_time
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept, shots["right"].shot_vector)
        elif agent.me.airborne:
            agent.push(recovery())
            agent.plan = TMCPMessage.ready_action(agent.team, agent.index, -1.0)
        else:
            agent.push(short_shot(agent.foe_goal.location))
            agent.plan = TMCPMessage.ball_action(agent.team, agent.index, agent.me.intercept)
    elif isinstance(agent.stack[-1], goto):
        agent.pop()

def attackOld(agent):
    if len(agent.stack) < 1:
        ball_to_me = agent.ball.location - agent.me.location
        targets = {"goal":(agent.foe_goal.left_post - Vector3(0, 0, 300), agent.foe_goal.right_post + Vector3(0, 0, 300))}
        shots = find_shots(agent, targets, 0)
        if shots["goal"] != None:
            agent.push(shots["goal"])
        else:
            agent.push(short_shot(agent.foe_goal.location))
    elif isinstance(agent.stack[-1], goto):
        agent.pop()

def saveOld(agent):
    if len(agent.stack) < 1:
        ball_to_me = agent.ball.location - agent.me.location
        upfield_left = Vector3(-side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 2000, 0)
        upfield_right = Vector3(side(agent.team) * 4096, agent.ball.location.y - side(agent.team) * 2000, 1000)
        targets = {"goal":(agent.foe_goal.left_post - Vector3(0, 0, 300), agent.foe_goal.right_post + Vector3(0, 0, 300)), "upfield":(upfield_left, upfield_right)}
        shots = find_shots(agent, targets, 0)
        if shots["upfield"] != None:
            agent.push(shots["upfield"])
        elif shots["goal"] != None:
            agent.push(shots["goal"])
        else:
            agent.push(short_shot(agent.foe_goal.location))
    elif isinstance(agent.stack[-1], goto):
        agent.pop()