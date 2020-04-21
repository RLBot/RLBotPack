from GoslingUtils.utils import *


def is_closest_kickoff(agent, own_car):
    # distance is calculated as distance + index - boost
    # boost added to allow the bot with the most boost to go for the ball in situations
    # were 2 bots are more or less equally close
    if not len(agent.friends):
        return True
    own_distance = (own_car.location - agent.ball.location).magnitude() + own_car.index
    for car in agent.friends + [agent.me]:
        if own_car.index == car.index:
            continue
        other_distance = (car.location - agent.ball.location).magnitude() + car.index
        if other_distance < own_distance:
            return False
    return True


def is_second_closest_kickof(agent):
    if is_closest_kickoff(agent, agent.me):
        return False
    if len(agent.friends) < 1:
        return False
    own_distance = (agent.me.location - agent.ball.location).magnitude() + agent.me.index
    closest_index = -1
    for car in agent.friends:
        if is_closest_kickoff(agent, car):
            closest_index = car.index

    if closest_index == agent.index:
        return False
    for car in agent.friends:
        if car.index == closest_index:
            continue
        other_distance = (car.location - agent.ball.location).magnitude() + car.index
        if other_distance < own_distance:
            return False
    return True


def is_closest(agent, own_car, team_only=False):
    # distance is calculated as distance + index - boost
    # boost added to allow the bot with the most boost to go for the ball in situations
    # were 2 bots are more or less equally close
    if not len(agent.friends) and team_only:
        return True

    ahead_counts = True if team_only and are_no_bots_back(agent) else False

    if is_ahead_of_ball(agent) and not ahead_counts:
        return False
    factor = 1
    if agent.me.location[1] * side(agent.team) < agent.ball.location[1] * side(agent.team):
        factor = 5
    if team_only:
        actual_distance_vector = own_car.location - agent.ball.location
        biased_distance_vector = Vector3(2 * actual_distance_vector[0], factor * actual_distance_vector[1],
                                         actual_distance_vector[2])
        own_distance = (biased_distance_vector).magnitude() - (10 * own_car.boost)
    else:
        own_distance = (own_car.location - agent.ball.location).magnitude() * factor - (10 * own_car.boost)
    if not team_only:
        for car in agent.foes:
            factor = 1
            if -car.location[1] * side(agent.team) < -agent.ball.location[1] * side(agent.team):
                factor = 5
            other_distance = (car.location - agent.ball.location).magnitude() * factor - (10 * car.boost)
            if other_distance < own_distance:
                return False
    for car in agent.friends + [agent.me]:
        if own_car.index == car.index:
            continue
        factor = 1
        if car.location[1] * side(agent.team) < agent.ball.location[1] * side(agent.team):
            factor = 5

        if team_only:
            other_actual_distance_vector = car.location - agent.ball.location
            other_biased_distance_vector = Vector3(2 * other_actual_distance_vector[0],
                                                   factor * other_actual_distance_vector[1],
                                                   other_actual_distance_vector[2])
            other_distance = (other_biased_distance_vector).magnitude() - (10 * car.boost)
        else:
            other_distance = (car.location - agent.ball.location).magnitude() * factor - (10 * car.boost)
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
    factor = 1
    if agent.me.location[1] * side(agent.team) < agent.ball.location[1] * side(agent.team):
        factor = 5

    actual_distance_vector = agent.me.location - agent.ball.location
    biased_distance_vector = Vector3(2 * actual_distance_vector[0], factor * actual_distance_vector[1],
                                     actual_distance_vector[2])
    own_distance = (biased_distance_vector).magnitude() - (10 * agent.me.boost)
    closest_index = -1
    for car in agent.friends:
        if is_closest(agent, car, True):
            closest_index = car.index

    if closest_index == agent.index:
        return False
    for car in agent.friends:
        if car.index == closest_index:
            continue
        factor = 1
        if car.location[1] * side(agent.team) < agent.ball.location[1] * side(agent.team):
            factor = 5

        other_actual_distance_vector = car.location - agent.ball.location
        other_biased_distance_vector = Vector3(2 * other_actual_distance_vector[0],
                                               factor * other_actual_distance_vector[1],
                                               other_actual_distance_vector[2])
        other_distance = (other_biased_distance_vector).magnitude() - (10 * car.boost)
        if other_distance < own_distance:
            return False
    return True


def is_ball_going_towards_goal(agent):
    if not agent.ball.velocity[1]:
        return False
    if agent.ball.velocity[1] * side(agent.team) < 0:
        return False
    ball_position_x = agent.ball.location[0] * side(agent.team)
    ball_position_y = agent.ball.location[1] * side(agent.team)
    ball_velocity_x = agent.ball.velocity[0] * side(agent.team)
    ball_velocity_y = agent.ball.velocity[1] * side(agent.team)
    m = ball_velocity_x / ball_velocity_y
    y = 5120 - ball_position_y
    x = m * y + ball_position_x
    return x >= -896 and x <= 893


def is_ball_on_back_wall(agent, enemy=True):
    y = side(agent.team) * -4950
    if not enemy:
        y *= -1
    possible = False
    if agent.team == 0:
        if (agent.ball.location[1] > y and enemy) or (agent.ball.location[1] < y and not enemy):
            possible = True

    if agent.team == 1:
        if (agent.ball.location[1] < y and enemy) or (agent.ball.location[1] > y and not enemy):
            possible = True

    if possible and abs(agent.ball.location[0]) < 1000:
        if agent.ball.location[2] > 1100:
            return True
        return False
    return False


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
    goal = 2 if agent.team == 1 else 8
    for car in agent.friends:
        zone = get_location_zone(car.location)
        zone_5, center = zone_5_positioning(agent)
        if zone in possible_zones:
            if zone == goal:
                if is_ball_centering(agent, True) or (get_location_zone(agent.ball.location) == 5):
                    if friendly_cars_in_front_of_goal(agent) < 2:
                        continue
                if (car.location - agent.friend_goal.location).magnitude() > (
                        agent.me.location - agent.friend_goal.location).magnitude():
                    continue
                else:
                    possible_zones.remove(zone)
            elif zone == 5 and center:
                if (car.location - zone_5).magnitude() < (agent.me.location - zone_5).magnitude():
                    possible_zones.remove(zone)
            elif (car.location - zone_center(zone)).magnitude() < (agent.me.location - zone_center(zone)).magnitude():
                possible_zones.remove(zone)
    return possible_zones


def friendly_cars_in_front_of_goal(agent):
    count = 0
    goal = 2 if agent.team == 1 else 8
    for car in agent.friends:
        if get_location_zone(car.location) == goal:
            count += 1
    return count


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
    if 5 in zones:
        return 5
    if 8 in zones:
        return 8
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
    if zone == 2 or zone == 8:
        return Vector3(0, -5000 if zone == 8 else 5000, 0)
    if zone < 4:
        y = 4520.0
    if zone > 6:
        y = -4520.0
    if zone == 1 or zone == 4 or zone == 7:
        x = 2.0 * 1356.0
    if zone == 3 or zone == 6 or zone == 9:
        x = -2.0 * 1356.0
    return Vector3(x, y, z)


def zone_5_positioning(agent):
    center = is_ball_centering(agent)
    ball_y = agent.ball.location[1]
    d_y = ball_y + 1707 * side(agent.team)
    return Vector3(0, 2 * d_y / 3, 0), center


def are_no_bots_back(agent):
    if not is_ahead_of_ball(agent) or is_closest(agent, agent.me):
        return False
    for car in agent.friends:
        if not is_ahead_of_ball_2(agent, car.location, agent.team):
            return False
    return True


def is_ball_centering(agent, friendly=False):
    struct = agent.get_ball_prediction_struct()
    for i in range(15, struct.num_slices, 10):
        ball_location = Vector3(struct.slices[i].physics.location)
        if abs(ball_location[0]) < 1500:
            if ball_location[1] * side(agent.team) < -3000 and not friendly:
                if ball_location[2] < 1500:
                    return True
            elif ball_location[1] * side(agent.team) > 3000 and friendly:
                if ball_location[2] < 1500:
                    return True
    return False


def opponent_car_by_index(agent, index):
    for car in agent.foes:
        if car.index == index:
            return car


def demo_rotation(agent):
    possible_cars = []
    for car in agent.foes:
        if car.location[1] * side(agent.team) < -4000:
            distance_to_target = (agent.me.location - car.location).magnitude()
            velocity = (agent.me.velocity).magnitude()
            velocity_needed = 2200 - velocity
            time_boosting_required = velocity_needed / 991.666
            boost_required = 33.3 * time_boosting_required
            distance_required = velocity * time_boosting_required + 0.5 * 991.666 * (time_boosting_required ** 2)
            if velocity < 2200:
                if agent.me.boost < boost_required:
                    continue
                elif distance_required > distance_to_target:
                    continue
                possible_cars.append(car)
            else:
                possible_cars.append(car)
    if not len(possible_cars):
        return False, -1
    if len(possible_cars) == 1:
        return True, possible_cars[0].index
    else:
        possible_cars.sort(key=lambda car: (agent.foe_goal.location - car.location).magnitude())
        return True, possible_cars[0].index


def friends_ahead_of_ball(agent):
    count = 0
    for car in agent.friends:
        if (car.location[1] > agent.ball.location[1] + 500 and agent.team == 0) or (
                car.location[1] < agent.ball.location[1] - 500 and agent.team == 1):
            count += 1
    return count

def is_last_one_back(agent):
    # don't use on defence
    my_y = agent.me.location[1] * side(agent.team)
    for car in agent.friends:
        if car.location[1] * side(agent.team) > my_y:
            return False
    return True

