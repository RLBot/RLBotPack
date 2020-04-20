from routines import *

#This file is for strategic tools

def find_hits(agent,targets):
    #find_hits takes a dict of (left,right) target pairs and finds routines that could hit the ball between those target pairs
    #find_hits is only meant for routines that require a defined intercept time/place in the future
    #find_hits should not be called more than once in a given tick, as it has the potential to use an entire tick to calculate

    #Example Useage:
    #targets = {"goal":(opponent_left_post,opponent_right_post), "anywhere_but_my_net":(my_right_post,my_left_post)}
    #hits = find_hits(agent,targets)
    #print(hits)
    #>{"goal":[a ton of jump and aerial routines,in order from soonest to latest], "anywhere_but_my_net":[more routines and stuff]}
    hits = {name:[] for name in targets}
    struct = agent.get_ball_prediction_struct()
    
    #Begin looking at slices 0.25s into the future
    #The number of slices 
    i = 15
    while i < struct.num_slices:
        #Gather some data about the slice
        intercept_time = struct.slices[i].game_seconds
        time_remaining = intercept_time - agent.time
        if time_remaining > 0:
            ball_location = Vector3(struct.slices[i].physics.location)
            ball_velocity = Vector3(struct.slices[i].physics.velocity).magnitude()

            if abs(ball_location[1]) > 5250:
                break #abandon search if ball is scored at/after this point
        
            #determine the next slice we will look at, based on ball velocity (slower ball needs fewer slices)
            i += 15 - cap(int(ball_velocity//150),0,13)
            
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
            forward_flag = forward_time > 0.0 and (distance*1.05 / forward_time) < (2290 if agent.me.boost > distance/100 else 1400)
            backward_flag = distance < 1500 and backward_time > 0.0 and (distance*1.05 / backward_time) < 1200
            
            #Provided everything checks out, we begin to look at the target pairs
            if forward_flag or backward_flag:
                for pair in targets:
                    #First we correct the target coordinates to account for the ball's radius
                    #If swapped == True, the shot isn't possible because the ball wouldn't fit between the targets
                    left,right,swapped = post_correction(ball_location,targets[pair][0],targets[pair][1])
                    if not swapped:
                        #Now we find the easiest direction to hit the ball in order to land it between the target points
                        left_vector = (left - ball_location).normalize()
                        right_vector = (right - ball_location).normalize()
                        best_shot_vector = direction.clamp(left_vector,right_vector)
                        
                        #Check to make sure our approach is inside the field
                        if in_field(ball_location - (200*best_shot_vector),1):
                            #The slope represents how close the car is to the chosen vector, higher = better
                            #A slope of 1.0 would mean the car is 45 degrees off
                            slope = find_slope(best_shot_vector,car_to_ball)
                            if forward_flag:
                                if ball_location[2] <= 300 and slope > 0.0:
                                    hits[pair].append(jump_shot(ball_location,intercept_time,best_shot_vector,slope))
                                elif 300 < ball_location[2] < 600 and slope > 1.0 and (ball_location[2]-250) * 0.14 < agent.me.boost:
                                    hits[pair].append(aerial_shot(ball_location,intercept_time,best_shot_vector,slope))
                                elif ball_location.z > 600:
                                    aerial = Aerial(ball_location, intercept_time, True, target=best_shot_vector)
                                    if aerial.is_viable(agent, agent.time):
                                        hits[pair].append(aerial)
                            elif backward_flag and ball_location[2] <= 280 and slope > 0.25:
                                hits[pair].append(jump_shot(ball_location,intercept_time,best_shot_vector,slope,-1))
    return hits
