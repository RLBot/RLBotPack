import math

from RLUtilities.LinearAlgebra import normalize, rotation, vec3, vec2, dot
from RLUtilities.Maneuvers import AirDodge

from util import line_backline_intersect, cap, distance_2d, sign, get_speed, powerslide, can_dodge


def defending(agent):
    target = defending_target(agent)
    agent.drive.target_pos = target
    agent.drive.target_speed = get_speed(agent, target)
    agent.drive.step(agent.FPS)
    agent.controls = agent.drive.controls
    powerslide(agent)
    if can_dodge(agent, target):
        agent.step = "Dodge"
        agent.dodge = AirDodge(agent.info.my_car, 0.1, target)
    if not agent.defending:
        agent.step = "Catching"
    if not agent.info.my_car.on_ground:
        agent.step = "Recovery"


def defending_target(agent):
    ball = agent.info.ball
    car = agent.info.my_car
    car_to_ball = ball.pos - car.pos
    backline_intersect = line_backline_intersect(agent.info.my_goal.center[1], vec2(car.pos), vec2(car_to_ball))
    if backline_intersect < 0:
        target = agent.info.my_goal.center - vec3(2000, 0, 0)
    else:
        target = agent.info.my_goal.center + vec3(2000, 0, 0)
    target_to_ball = normalize(ball.pos - target)
    target_to_car = normalize(car.pos - target)
    difference = target_to_ball - target_to_car
    error = cap(abs(difference[0]) + abs(difference[1]), 1, 10)

    goal_to_ball_2d = vec2(target_to_ball[0], target_to_ball[1])
    test_vector_2d = dot(rotation(0.5 * math.pi), goal_to_ball_2d)
    test_vector = vec3(test_vector_2d[0], test_vector_2d[1], 0)

    distance = cap((40 + distance_2d(ball.pos, car.pos) * (error ** 2)) / 1.8, 0, 4000)
    location = ball.pos + vec3((target_to_ball[0] * distance), target_to_ball[1] * distance, 0)

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
