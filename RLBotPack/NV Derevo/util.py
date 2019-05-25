import math

from RLUtilities.LinearAlgebra import vec2, norm, dot, vec3, normalize


def distance_2d(a, b):
    return norm(vec2(a - b))


def get_closest_small_pad(agent):
    pads = agent.info.small_boost_pads
    pad = None
    distance = math.inf
    for i in range(len(pads)):
        if distance_2d(agent.info.my_car.pos, pads[i].pos) < distance:
            distance = distance_2d(agent.info.my_car.pos, pads[i].pos)
            pad = pads[i]
    return pad


def line_backline_intersect(y, origin, direction):
    if abs(direction[1]) < 1e-10:
        direction[1] = 1e-10
    mult = (y - origin[1]) / direction[1]
    return (origin + mult * direction)[0]


def sign(x):
    if x <= 0:
        return -1
    else:
        return 1


def velocity_2d(vel):
    return norm(vec2(vel))


def boost_needed(initial_speed, goal_speed):
    p1 = 6.31e-06
    p2 = 0.010383
    p3 = 1.3183
    boost_initial = p1 * initial_speed ** 2 + p2 * initial_speed + p3
    boost_goal = p1 * goal_speed ** 2 + p2 * goal_speed + p3
    return boost_goal - boost_initial


def is_reachable(agent, location, eta):
    distance = distance_2d(agent.info.my_car.pos, location)
    if eta == 0:
        return False
    speed = distance / eta
    if speed < 2300:
        if speed < 1399:
            return True
        return agent.info.my_car.boost > boost_needed(velocity_2d(agent.info.my_car.vel), speed)


def powerslide(agent):
    target_local = dot(agent.drive.target_pos - agent.info.my_car.pos, agent.info.my_car.theta)
    phi = math.atan2(target_local[1], target_local[0])
    if abs(phi) > 1.7:
        agent.controls.handbrake = 1
        agent.controls.boost = 0


def get_speed(agent, location):
    car = agent.info.my_car
    local = dot(location - car.pos, car.theta)
    angle = cap(math.atan2(local[1], local[0]), -3, 3)
    distance = distance_2d(car.pos, location)
    if distance > 2.5 * velocity_2d(car.vel):
        return 2250
    else:
        return 2250 - (400 * (angle ** 2))


def can_dodge(agent, target):
    bot_to_target = target - agent.info.my_car.pos
    local_bot_to_target = dot(bot_to_target, agent.info.my_car.theta)
    angle_front_to_target = math.atan2(local_bot_to_target[1], local_bot_to_target[0])
    distance_bot_to_target = norm(vec2(bot_to_target))
    good_angle = math.radians(-10) < angle_front_to_target < math.radians(10)
    on_ground = agent.info.my_car.on_ground and agent.info.my_car.pos[2] < 100
    going_fast = velocity_2d(agent.info.my_car.vel) > 1250
    target_not_in_goal = not agent.info.my_goal.inside(target)
    return good_angle and distance_bot_to_target > 2000 and on_ground and going_fast and target_not_in_goal


def cap(x, low, high):
    if x < low:
        return low
    elif x > high:
        return high
    else:
        return x


def get_bounce(agent):
    for i in range(len(agent.bounces)):
        goal_to_ball = normalize(z0(agent.bounces[i][0] - agent.info.their_goal.center))
        target = agent.bounces[i][0] + 40 * goal_to_ball
        if is_reachable(agent, target, agent.bounces[i][1]):
            return [target, agent.bounces[i][1]]


def z0(vector):
    return vec3(vector[0], vector[1], 0)

# def speed(agent, location):
#     distance = distance_2d(agent.info.my_car.pos, location)
#
#     alpha = 1.3
#     time_left = agent.eta - agent.time
#     avg_vf = distance / time_left
#     target_vf = (1.0 - alpha) * velocity_2d(agent.info.my_car.vel) + alpha * avg_vf
#
#     if velocity_2d(agent.info.my_car.vel) < target_vf:
#         agent.controls.throttle = 1.0
#         if target_vf > 1399:
#             agent.controls.boost = 1
#         else:
#             agent.controls.boost = 0
#     else:
#         if velocity_2d(agent.info.my_car.vel) - target_vf > 75:
#             agent.controls.throttle = -1.0
#         else:
#             agent.controls.throttle = 0.0
