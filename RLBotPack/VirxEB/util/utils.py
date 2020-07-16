import math
from queue import Full

from util.objects import Vector


def almost_equals(x, y, threshold):
    return x - threshold < y and y < x + threshold


def backsolve(target, car, time, gravity):
    # Finds the acceleration required for a car to reach a target in a specific amount of time
    d = target - car.location
    dvx = ((d.x/time) - car.velocity.x) / time
    dvy = ((d.y/time) - car.velocity.y) / time
    dvz = (((d.z/time) - car.velocity.z) / time) + (gravity * -1 * time)
    return Vector(dvx, dvy, dvz)


def cap(x, low, high):
    # caps/clamps a number between a low and high value
    return max(min(x, high), low)


def defaultPD(agent, local_target, direction=1.0):
    # points the car towards a given local target.
    # Direction can be changed to allow the car to steer towards a target while driving backwards
    local_target *= direction
    up = agent.me.local(Vector(z=1))  # where "up" is in local coordinates
    target_angles = (
        math.atan2(local_target.z, local_target.x),  # angle required to pitch towards target
        math.atan2(local_target.y, local_target.x),  # angle required to yaw towards target
        math.atan2(up.y, up.z)  # angle required to roll upright
    )
    # Once we have the angles we need to rotate, we feed them into PD loops to determing the controller inputs
    agent.controller.steer = steerPD(target_angles[1], 0) * direction
    agent.controller.pitch = steerPD(target_angles[0], agent.me.angular_velocity.y/4)
    agent.controller.yaw = steerPD(target_angles[1], -agent.me.angular_velocity.z/4)
    agent.controller.roll = steerPD(target_angles[2], agent.me.angular_velocity.x/2)
    # Returns the angles, which can be useful for other purposes
    return target_angles


def defaultThrottle(agent, target_speed, direction=1.0):
    # accelerates the car to a desired speed using throttle and boost
    car_speed = agent.me.local(agent.me.velocity).x
    t = (target_speed * direction) - car_speed
    agent.controller.throttle = cap((t**2) * sign(t)/1000, -1.0, 1.0)
    agent.controller.boost = t > 150 and 1000 < car_speed and car_speed < 2275 and agent.controller.throttle == 1.0
    return car_speed


def in_field(point, radius):
    # determines if a point is inside the standard soccer field
    point = Vector(abs(point.x), abs(point.y), abs(point.z))
    if point.x > 4080 - radius:
        return False
    elif point.y > 5900 - radius:
        return False
    elif point.x > 880 - radius and point.y > 5105 - radius:
        return False
    elif point.x > 2650 and point.y > -point.x + 8025 - radius:
        return False
    return True


def find_slope(shot_vector, car_to_target):
    # Finds the slope of your car's position relative to the shot vector (shot vector is y axis)
    # 10 = you are on the axis and the ball is between you and the direction to shoot in
    # -10 = you are on the wrong side
    # 1.0 = you're about 45 degrees offcenter
    d = shot_vector.dot(car_to_target)
    e = abs(shot_vector.cross(Vector(z=1)).dot(car_to_target))
    try:
        f = d / e
    except ZeroDivisionError:
        return 10*sign(d)
    return cap(f, -3, 3)


def post_correction(ball_location, left_target, right_target):
    # this function returns target locations that are corrected to account for the ball's radius
    # If the left and right post swap sides, a goal cannot be scored
    # We purposly make this a bit larger so that our shots have a higher chance of success
    ball_radius = 120
    goal_line_perp = (right_target - left_target).cross(Vector(z=1))
    left = left_target + ((left_target - ball_location).normalize().cross(Vector(z=-1))*ball_radius)
    right = right_target + ((right_target - ball_location).normalize().cross(Vector(z=1))*ball_radius)
    left = left_target if (left-left_target).dot(goal_line_perp) > 0 else left
    right = right_target if (right-right_target).dot(goal_line_perp) > 0 else right
    swapped = True if (left - ball_location).normalize().cross(Vector(z=1)).dot((right - ball_location).normalize()) > -0.1 else False
    return left, right, swapped


def quadratic(a, b, c):
    # Returns the two roots of a quadratic
    inside = math.sqrt((b*b) - (4*a*c))
    if a != 0:
        return (-b + inside)/(2*a), (-b - inside)/(2*a)

    return -1, -1


def shot_valid(agent, shot, threshold=45, target=None):
    # Returns True if the ball is still where the shot anticipates it to be
    if target is None:
        target = shot.ball_location

    # First finds the two closest slices in the ball prediction to shot's intercept_time
    # threshold controls the tolerance we allow the ball to be off by
    slices = agent.predictions['ball_struct'].slices
    soonest = 0
    latest = len(slices)-1
    while len(slices[soonest:latest+1]) > 2:
        midpoint = (soonest+latest) // 2
        if slices[midpoint].game_seconds > shot.intercept_time:
            latest = midpoint
        else:
            soonest = midpoint
    # preparing to interpolate between the selected slices
    dt = slices[latest].game_seconds - slices[soonest].game_seconds
    time_from_soonest = shot.intercept_time - slices[soonest].game_seconds
    soonest = (slices[soonest].physics.location.x, slices[soonest].physics.location.y, slices[soonest].physics.location.z)
    slopes = (Vector(slices[latest].physics.location.x, slices[latest].physics.location.y, slices[latest].physics.location.z) - Vector(*soonest)) * (1/dt)
    # Determining exactly where the ball will be at the given shot's intercept_time
    predicted_ball_location = Vector(*soonest) + (slopes * time_from_soonest)
    # Comparing predicted location with where the shot expects the ball to be
    return target.dist(predicted_ball_location) < threshold


def side(x):
    # returns -1 for blue team and 1 for orange team
    if x == 0:
        return -1
    return 1


def sign(x):
    # returns the sign of a number, -1, 0, +1
    if x < 0:
        return -1

    if x > 0:
        return 1

    return 0


def steerPD(angle, rate):
    # A Proportional-Derivative control loop used for defaultPD
    return cap(((35*(angle+rate))**3)/10, -1.0, 1.0)


def lerp(a, b, t):
    # Linearly interpolate from a to b using t
    # For instance, when t == 0, a is returned, and when t is 1, b is returned
    # Works for both numbers and Vectors
    return (b - a) * t + a


def invlerp(a, b, v):
    # Inverse linear interpolation from a to b with value v
    # For instance, it returns 0 if v is a, and returns 1 if v is b, and returns 0.5 if v is exactly between a and b
    # Works for both numbers and Vectors
    return (v - a)/(b - a)


def send_comm(agent, msg):
    message = {
        "index": agent.index,
        "team": agent.team
    }
    msg.update(message)
    try:
        agent.matchcomms.outgoing_broadcast.put_nowait({
            "VirxEB": msg
        })
    except Full:
        agent.print("Outgoing broadcast is full; couldn't send message")


def get_weight(agent, shot=None, index=None):
    if index is not None:
        return agent.max_shot_weight - math.ceil(index / 2)

    if shot is not None:
        for shot_list in (agent.offensive_shots, agent.defensive_shots):
            try:
                return agent.max_shot_weight - math.ceil(shot_list.index(shot) / 2)
            except ValueError:
                continue


def peek_generator(generator):
    try:
        return next(generator)
    except StopIteration:
        return None
