import math

from RLUtilities.LinearAlgebra import normalize, rotation, vec3, vec2, dot
from RLUtilities.Maneuvers import Drive, AirDodge, norm

from util import cap, distance_2d, sign, line_backline_intersect, get_speed, powerslide


def start_shooting(agent):
    agent.step = "Shooting"
    target = shooting_target(agent)
    speed = get_speed(agent, target)
    agent.drive = Drive(agent.info.my_car, target, speed)


def shooting(agent):
    agent.drive.step(agent.FPS)
    agent.controls = agent.drive.controls
    powerslide(agent)
    target = shooting_target(agent)
    agent.drive.target_pos = target
    agent.drive.target_speed = get_speed(agent, target)
    if should_dodge(agent):
        agent.step = "Dodge"
        agent.dodge = AirDodge(agent.info.my_car, 0.1, agent.info.ball.pos)
    elif not (abs(agent.info.ball.vel[2]) < 100 and sign(agent.team) * agent.info.ball.vel[1] < 0):
        agent.step = "Catching"
        agent.drive = Drive(agent.info.my_car, agent.info.ball.pos, 1399)


def shooting_target(agent):
    ball = agent.info.ball
    car = agent.info.my_car
    car_to_ball = ball.pos - car.pos
    backline_intersect = line_backline_intersect(agent.info.their_goal.center[1], vec2(car.pos), vec2(car_to_ball))
    if -500 < backline_intersect < 500:
        goal_to_ball = normalize(car.pos - ball.pos)
        error = cap(distance_2d(ball.pos, car.pos) / 1000, 0, 1)
    else:
        # Right of the ball
        if -500 > backline_intersect:
            target = agent.info.their_goal.corners[3] + vec3(400, 0, 0)
        # Left of the ball
        elif 500 < backline_intersect:
            target = agent.info.their_goal.corners[2] - vec3(400, 0, 0)
        goal_to_ball = normalize(ball.pos - target)
        goal_to_car = normalize(car.pos - target)
        difference = goal_to_ball - goal_to_car
        error = cap(abs(difference[0]) + abs(difference[1]), 1, 10)

    goal_to_ball_2d = vec2(goal_to_ball[0], goal_to_ball[1])
    test_vector_2d = dot(rotation(0.5 * math.pi), goal_to_ball_2d)
    test_vector = vec3(test_vector_2d[0], test_vector_2d[1], 0)

    distance = cap((40 + distance_2d(ball.pos, car.pos) * (error ** 2)) / 1.8, 0, 4000)
    location = ball.pos + vec3((goal_to_ball[0] * distance), goal_to_ball[1] * distance, 0)

    # this adjusts the target based on the ball velocity perpendicular to the direction we're trying to hit it
    multiplier = cap(distance_2d(car.pos, location) / 1500, 0, 2)
    distance_modifier = cap(dot(test_vector, ball.vel) * multiplier, -1000, 1000)
    modified_vector = vec3(test_vector[0] * distance_modifier, test_vector[1] * distance_modifier, 0)
    location += modified_vector

    # another target adjustment that applies if the ball is close to the wall
    extra = 3850 - abs(location[0])
    if extra < 0:
        location[0] = cap(location[0], -3850, 3850)
        location[1] = location[1] + (-sign(agent.team) * cap(extra, -800, 800))
    return location


def should_dodge(agent):
    car = agent.info.my_car
    their_goal = agent.info.their_goal
    close_to_goal = distance_2d(car.pos, their_goal.center) < 4000
    aiming_for_goal = abs(line_backline_intersect(their_goal.center[1], vec2(car.pos), vec2(car.forward()))) < 850
    bot_to_target = agent.info.ball.pos - car.pos
    local_bot_to_target = dot(bot_to_target, agent.info.my_car.theta)
    angle_front_to_target = math.atan2(local_bot_to_target[1], local_bot_to_target[0])
    close_to_ball = norm(vec2(bot_to_target)) < 850
    good_angle = math.radians(-10) < angle_front_to_target < math.radians(10)
    return close_to_ball and close_to_goal and aiming_for_goal and good_angle
