import math
from objects import Vector3

#This file is for small utilities for math and movement

def backsolve(target, car, time, gravity = 650):
    #Finds the acceleration required for a car to reach a target in a specific amount of time
    d = target - car.location
    dvx = ((d[0]/time) - car.velocity[0]) / time
    dvy = ((d[1]/time) - car.velocity[1]) / time
    dvz = (((d[2]/time) - car.velocity[2]) / time) + (gravity * time)
    return Vector3(dvx,dvy,dvz)

def cap(x, low, high):
    #caps/clamps a number between a low and high value
    if x < low:
        return low
    elif x > high:
        return high
    return x

def defaultPD(agent, local_target, direction = 1.0):
    #points the car towards a given local target.
    #Direction can be changed to allow the car to steer towards a target while driving backwards
    local_target *= direction
    up = agent.me.local(Vector3(0,0,1)) #where "up" is in local coordinates
    target_angles = [
        math.atan2(local_target[2],local_target[0]), #angle required to pitch towards target
        math.atan2(local_target[1],local_target[0]), #angle required to yaw towards target
        math.atan2(up[1],up[2])]                     #angle required to roll upright
    #Once we have the angles we need to rotate, we feed them into PD loops to determing the controller inputs
    agent.controller.steer = steerPD(target_angles[1],0) * direction
    agent.controller.pitch = steerPD(target_angles[0],agent.me.angular_velocity[1]/4)
    agent.controller.yaw = steerPD(target_angles[1],-agent.me.angular_velocity[2]/4)
    agent.controller.roll = steerPD(target_angles[2],agent.me.angular_velocity[0]/2)
    #Returns the angles, which can be useful for other purposes
    return target_angles

def defaultThrottle(agent, target_speed, direction = 1.0):
    #accelerates the car to a desired speed using throttle and boost
    car_speed = agent.me.local(agent.me.velocity)[0]
    t = (target_speed * direction) - car_speed
    agent.controller.throttle = cap((t**2) * sign(t)/1000, -1.0, 1.0)
    agent.controller.boost = True if t > 150 and car_speed < 2275 and agent.controller.throttle == 1.0 else False
    return car_speed

def in_field(point,radius):
    #determines if a point is inside the standard soccer field
    point = Vector3(abs(point[0]),abs(point[1]),abs(point[2]))
    if point[0] > 4080 - radius:
        return False
    elif point[1] > 5060 - radius:
        return False
    elif point[0] > 880 - radius and point[1] > 5105 - radius:
        return False
    elif point[0] > 2650 and point[1] > -point[0] + 8025 - radius:
        return False
    return True

def on_wall(point):
    #determines if a point is on the wall
    point = Vector3(abs(point[0]),abs(point[1]),abs(point[2]))
    if point[2] > 400:
        if point[0] > 3600 and 4000 > point[1]:
            return True
        elif 900 < point[0] < 3000 and point[1] > 4900:
            return True
        elif point[0] > 2900 and point[1] > 3800 and 7500 < point[0] + point[1] < 8500:
            return True
        else:
            return False
    else:
        return False

def distance_to_wall(point):
    #determines how close the car is to the wall
    point = Vector3(abs(point[0]), abs(point[1]), abs(point[2]))
    if 4096 - point[0] < 5120 - point[1]:
        return 4096 - point[0]
    else:
        return 5120 - point[1]

def eta(car, ball_location):
    car_to_ball = ball_location - car.location
    # Adding a True to a vector's normalize will have it also return the magnitude of the vector
    direction, distance = car_to_ball.normalize(True)

    # How far the car must turn in order to face the ball, for forward and reverse
    forward_angle = direction.angle(car.orientation[0])
    backward_angle = math.pi - forward_angle

    vel_in_direction = car.velocity.dot(direction)
    # If the car only had to drive in a straight line, we ensure it has enough time to reach the ball (a few assumptions are made)
    forward_time = (distance * 1.05) / cap(vel_in_direction + 1000 * car.boost / 30, 1410, 2300) + (forward_angle * 0.318)
    backward_time = (distance * 1.05) / 1400 + (backward_angle * 0.418)

    if forward_time < backward_time or distance > 1500:
        return forward_time,True
    else:
        return backward_time,False

def find_rotation(agent, friend):
    my_car_to_ball = agent.ball.location - agent.me.location
    friend_car_to_ball = agent.ball.location - friend.location

    my_distance = my_car_to_ball.magnitude()
    friend_distance = friend_car_to_ball.magnitude()

    goal_to_ball, my_ball_distance = (agent.ball.location - agent.friend_goal.location).normalize(True)
    goal_to_me, my_goal_distance = (agent.me.location - agent.friend_goal.location).normalize(True)
    goal_to_friend, friend_goal_distance = (friend.location - agent.friend_goal.location).normalize(True)

    me_back = my_goal_distance - 200 < my_ball_distance
    friend_back = friend_goal_distance - 200 < my_ball_distance

    my_direction = my_car_to_ball.normalize()
    friend_direction = friend_car_to_ball.normalize()

    left_vector = (agent.foe_goal.left_post - agent.ball.location).normalize()
    right_vector = (agent.foe_goal.right_post  - agent.ball.location).normalize()
    my_best_shot_vector = my_direction.clamp(left_vector, right_vector)
    friend_best_shot_vector = friend_direction.clamp(left_vector, right_vector)

    my_angle = my_best_shot_vector.angle(my_car_to_ball)
    friend_angle = friend_best_shot_vector.angle(friend_car_to_ball)

    return (not agent.kickoff_flag and friend_distance + friend_goal_distance * (friend_angle / math.pi) < my_distance + my_goal_distance * (my_angle / math.pi) and friend_back == me_back) or (friend_back and not me_back) \
             or (agent.kickoff_flag and friend_distance + 50 < my_distance) or (agent.kickoff_flag and abs(friend_distance - my_distance) < 100 and sign(agent.me.location.x) == side(agent.team))

def find_slope(shot_vector,car_to_target):
    #Finds the slope of your car's position relative to the shot vector (shot vector is y axis)
    #10 = you are on the axis and the ball is between you and the direction to shoot in
    #-10 = you are on the wrong side
    #1.0 = you're about 45 degrees offcenter
    d = shot_vector.dot(car_to_target)
    e = abs(shot_vector.cross((0,0,1)).dot(car_to_target))
    return cap(d / e if e != 0 else 10*sign(d), -3.0,3.0)

def post_correction(ball_location, left_target, right_target):
    #this function returns target locations that are corrected to account for the ball's radius
    #If the left and right post swap sides, a goal cannot be scored
    ball_radius = 120 #We purposly make this a bit larger so that our shots have a higher chance of success
    goal_line_perp = (right_target - left_target).cross((0,0,1))
    left = left_target + ((left_target - ball_location).normalize().cross((0,0,-1))*ball_radius)
    right = right_target + ((right_target - ball_location).normalize().cross((0,0,1))*ball_radius)
    left = left_target if (left-left_target).dot(goal_line_perp) > 0.0 else left
    right = right_target if (right-right_target).dot(goal_line_perp) > 0.0 else right
    swapped = True if (left - ball_location).normalize().cross((0,0,1)).dot((right - ball_location).normalize()) > -0.1 else False
    return left,right,swapped

def quadratic(a,b,c):
    #Returns the two roots of a quadratic
    inside = math.sqrt((b*b) - (4*a*c))
    if a != 0:
        return (-b + inside)/(2*a),(-b - inside)/(2*a)
    else:
        return -1,-1

def shot_valid(agent, shot, threshold = 30):
    #Returns True if the ball is still where the shot anticipates it to be
    #First finds the two closest slices in the ball prediction to shot's intercept_time
    #threshold controls the tolerance we allow the ball to be off by
    slices = agent.get_ball_prediction_struct().slices
    soonest = 0
    latest = len(slices)-1
    while len(slices[soonest:latest+1]) > 2:
        midpoint = (soonest+latest) // 2
        if slices[midpoint].game_seconds > shot.intercept_time:
            latest = midpoint
        else:
            soonest = midpoint
    #preparing to interpolate between the selected slices
    dt = slices[latest].game_seconds - slices[soonest].game_seconds
    time_from_soonest = shot.intercept_time - slices[soonest].game_seconds
    slopes = (Vector3(slices[latest].physics.location) - Vector3(slices[soonest].physics.location)) * (1/dt)
    #Determining exactly where the ball will be at the given shot's intercept_time
    predicted_ball_location = Vector3(slices[soonest].physics.location) + (slopes * time_from_soonest)
    #Comparing predicted location with where the shot expects the ball to be
    return (shot.ball_location - predicted_ball_location).magnitude() < threshold

def side(x):
    #returns -1 for blue team and 1 for orange team
    if x == 0:
        return -1
    return 1
    
def sign(x):
    #returns the sign of a number, -1, 0, +1
    if x < 0.0:
        return -1
    elif x > 0.0:
        return 1
    else:
        return 0.0
    
def steerPD(angle, rate):
    #A Proportional-Derivative control loop used for defaultPD
    return cap(((35*(angle+rate))**3)/10, -1.0, 1.0)
