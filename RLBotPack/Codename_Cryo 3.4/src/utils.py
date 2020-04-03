from GoslingUtils.utils import *
from GoslingUtils.tools import *


def is_closest(agent, own_car, team_only=False):
    if not len(agent.friends) and team_only:
        return True

    ahead_counts = True if team_only and are_no_bots_back(agent) else False

    if is_ahead_of_ball(agent) and not ahead_counts:
        return False
    own_distance = (own_car.location - agent.ball.location).magnitude() + own_car.index
    if not team_only:
        for car in agent.foes:
            other_distance = (car.location - agent.ball.location).magnitude()
            if other_distance < own_distance:
                return False
    for car in agent.friends:
        other_distance = (car.location - agent.ball.location).magnitude() + car.index
        if is_ahead_of_ball_2(agent, car.location, agent.team) and not ahead_counts:
            continue
        if other_distance < own_distance:
            return False

    return True


def is_second_closest(agent):
    if is_closest(agent, agent.me, True):
        return False
    if is_ahead_of_ball(agent):
        return False
    if len(agent.friends) < 1:
        return False
    own_distance = (agent.me.location - agent.ball.location).magnitude() + agent.me.index * 3
    closest_index = -1
    for car in agent.friends:
        if is_closest(agent, car, True):
            closest_index = car.index

    if closest_index == agent.index:
        return False
    for car in agent.friends:
        if car.index == closest_index:
            continue
        other_distance = (car.location - agent.ball.location).magnitude() + car.index * 3
        if other_distance < own_distance:
            return False
    return True


def is_ball_going_towards_goal(agent):
    if not agent.ball.velocity[1]:
        return False
    m = agent.ball.velocity[0] / agent.ball.velocity[1]
    y = side(agent) * 5120 - agent.ball.location[1]
    x = m * y + agent.ball.location[0]
    return x >= -896 and x <= 893


def is_ball_on_back_wall(agent, enemy=True):
    y = side(agent.team) * -4950
    if not enemy:
        y *= -1
    if agent.team == 0:
        if (agent.ball.location[1] > y and enemy) or (agent.ball.location[1] < y and not enemy):
            return True

    if agent.team == 1:
        if (agent.ball.location[1] < y and enemy) or (agent.ball.location[1] > y and not enemy):
            return True

    if abs(agent.ball.location[0]) < 1000:
        if agent.ball.location[2] > 1100:
            return True
        return False
    return False


def determine_shot(agent, target, targets, target_count):
    if agent.ball.location[2] > 300 or agent.ball.velocity.magnitude() > 0:
        hits = find_hits(agent, targets)
        if len(hits):
            for i in range(1, 1 + target_count):
                if len(hits[str(i)]):
                    shot = hits[str(i)][0]
                    # max_boost_needed
                    if len(agent.stack): agent.pop()
                    agent.push(shot)
                    return
    if len(agent.stack): agent.pop()
    shot = short_shot(target)
    agent.push(shot)
    return


def is_ahead_of_ball(agent):
    return (agent.me.location[1] > agent.ball.location[1] + 500 and agent.team == 0) or (
            agent.me.location[1] < agent.ball.location[1] - 500 and agent.team == 1)


def is_ahead_of_ball_2(agent, location, team):
    return (location[1] > agent.ball.location[1] + 500 and team == 0) or (
            location[1] < agent.ball.location[1] - 500 and team == 1)


def get_desired_zone(agent):
    ball_zone = get_location_zone(agent.ball.location)
    possible_zones = []
    if agent.team == 0:
        if ball_zone >= 7:
            for i in range(7, 10):
                possible_zones.append(i)
        elif ball_zone >= 4:
            for i in range(7, 10):
                if ball_zone == 4 and i == 9:
                    continue
                if ball_zone == 6 and i == 7:
                    continue
                possible_zones.append(i)
        else:
            for i in range(4, 7):
                if ball_zone == 1 and i == 6:
                    continue
                if ball_zone == 3 and i == 4:
                    continue
                possible_zones.append(i)

    if agent.team == 1:
        if ball_zone <= 3:
            for i in range(1, 4):
                possible_zones.append(i)
        elif ball_zone <= 6:
            for i in range(1, 4):
                if ball_zone == 4 and i == 3:
                    continue
                if ball_zone == 6 and i == 1:
                    continue
                possible_zones.append(i)
        else:
            for i in range(4, 7):
                if ball_zone == 7 and i == 6:
                    continue
                if ball_zone == 9 and i == 4:
                    continue
                possible_zones.append(i)
    possible_zones = reduce_possible_zones(agent, possible_zones)
    if not len(possible_zones):
        return -1
    return get_closest_zone(agent, possible_zones)


def reduce_possible_zones(agent, possible_zones):
    for car in agent.friends:
        if car.index < agent.index:
            zone = get_location_zone(car.location)
            if zone in possible_zones:
                possible_zones.remove(zone)
    return possible_zones


def get_location_zone(vector):
    i = 1
    j = 2
    y = vector[1]
    x = vector[0]
    if (y >= 1707):
        i = 0
    elif (y <= -1707):
        i = 2
    if (x >= 1356):
        j = 1
    if (x <= -1356):
        j = 3
    return i * 3 + j


def get_closest_zone(agent, zones):
    closest = -1
    closest_distance = 9999999
    if 2 in zones:
        return 2
    if 4 in zones:
        return 4
    if 6 in zones:
        return 6
    for i in zones:
        if i == 10:
            print("HELP ZONE 10")
        x = 0
        y = 0
        if i < 4:
            y = 2 * 1707
        if i > 6:
            y = -2 * 1707
        if i == 1 or i == 4 or i == 7:
            x = 2 * 1356
        if i == 3 or i == 6 or i == 9:
            x = -2 * 1356
        distance = (agent.me.location - Vector3(x, y, 0)).magnitude()
        if distance < closest_distance:
            closest_distance = distance
            closest = i
    return closest


def zone_center(zone):
    if zone < 1 or zone > 9:
        return Vector3(0, 0, 0)
    x = 0
    y = 0
    z = 0
    if zone < 4:
        y = 4520.0
    if zone > 6:
        y = -4520.0
    if zone == 1 or zone == 4 or zone == 7:
        x = 2.0 * 1356.0
    if zone == 3 or zone == 6 or zone == 9:
        x = -2.0 * 1356.0
    return Vector3(x, y, z)


def are_no_bots_back(agent):
    if not is_ahead_of_ball(agent) or is_closest(agent, agent.me):
        return False
    for car in agent.friends:
        if not is_ahead_of_ball_2(agent, car.location, agent.team):
            return False
    return True
