from math import sqrt


def cap(x, low, high, allow_zero=True):
    if x < low:
        if x == 0.0 and not allow_zero:
            return 0.00001
        return low
    elif x > high:
        if x == 0.0 and not allow_zero:
            return -0.00001
        return high
    if x == 0.0 and not allow_zero:
        return 0.00001
    return x


def sign(x, allow_zero=True):
    if x > 0.0:
        return 1.0
    elif x < 0.0:
        return -1.0
    elif allow_zero:
        return 0.0
    else:
        return 1.0


def side(x):
    if x == 0:
        return -1
    return 1


def orient_pd(agent, target, backwards=False, up_axis=(0, 0, 1)):
    forward = (target - agent.car.location).normalize()
    if backwards:
        forward *= -1
    left = forward.cross(up_axis)
    up = forward.cross(left)

    # Credit to DomNomNom for this clever solution to finding the "angles" each axis must rotate
    # https://github.com/DomNomNom/RocketBot/blob/32e69df4f2841501c5f1da97ce34673dccb670af/NomBot_v1.5/NomBot_v1_5.py#L56
    rotation_axis = -forward.cross(agent.car.forward)
    rotation_up = -up.cross(agent.car.up)
    pitch_req = rotation_axis.dot(agent.car.left)
    yaw_req = rotation_axis.dot(agent.car.up)
    if backwards:
        yaw_req *= -1
    roll_req = rotation_up.dot(agent.car.forward)

    # these "angles" decrease past 90 degrees of error, so we force them to stay at 90 if the car is beyond 90
    if forward.dot(agent.car.forward) < 0:
        pitch_req = sign(pitch_req, False)
        yaw_req = sign(yaw_req, False)
    if up.dot(agent.car.up) > 0:
        roll_req = sign(roll_req, False)

    pitch_p_gain = 12
    yaw_p_gain = 8
    steer_p_gain = 10
    roll_p_gain = 10
    pitch_d_gain = -1.95
    yaw_d_gain = -1.47
    steer_d_gain = -0.25
    roll_d_gain = 0.65

    pitch = cap((pitch_req * pitch_p_gain) + (agent.car.angular_velocity[1] * pitch_d_gain), -1.0, 1.0)
    yaw = cap((yaw_req * yaw_p_gain) + (agent.car.angular_velocity[2] * yaw_d_gain), -1.0, 1.0)
    steer = cap((yaw_req * steer_p_gain) + (agent.car.angular_velocity[2] * steer_d_gain), -1.0, 1.0)
    roll = cap((roll_req * roll_p_gain) + (agent.car.angular_velocity[0] * roll_d_gain), -1.0, 1.0)
    return pitch, yaw, steer, roll


def throttle_p(agent, target_speed, use_boost=True):
    need_dodge = False
    current_speed = agent.car.velocity.dot(agent.car.forward) / 4600
    throttle_req = (target_speed / 4600) - current_speed

    throttle_p_gain = 95

    throttle = cap((throttle_req * throttle_p_gain), -1.0, 1.0)
    boost = use_boost and throttle_req > 0.0125 and current_speed < 0.4995

    if abs(current_speed) > 0.05 and throttle_req > 0.05 and (target_speed < 0 or agent.car.boost < 1 or not use_boost):
        need_dodge = True

    return throttle, boost, need_dodge


def time_to_fall(distance_to_ground, vertical_velocity):
    return quad(-325, vertical_velocity, distance_to_ground)


def quad(a, b, c):
    inside = (b ** 2) - (4 * a * c)
    if inside < 0 or a == 0:
        return 0.00001
    else:
        sq = sqrt(inside)
        n = (-b - sq) / (2 * a)
        p = (-b + sq) / (2 * a)
        if p > n:
            return p
        return n
