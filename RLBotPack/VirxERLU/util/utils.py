from queue import Full

from util.agent import math, Vector


def cap(x, low, high):
    # caps/clamps a number between a low and high value
    return max(min(x, high), low)


def cap_in_field(agent, target):
    if abs(target.x) > 893 - agent.me.hitbox.length:
        target.y = cap(target.y, -5120 + agent.me.hitbox.length, 5120 - agent.me.hitbox.length)
    target.x = cap(target.x, -893 + agent.me.hitbox.length, 893 - agent.me.hitbox.length) if abs(agent.me.location.y) > 5120 - (agent.me.hitbox.length / 2) else cap(target.x, -4093 + agent.me.hitbox.length, 4093 - agent.me.hitbox.length)

    return target


def defaultPD(agent, local_target, upside_down=False, up=None):
    # points the car towards a given local target.
    # Direction can be changed to allow the car to steer towards a target while driving backwards

    if up is None:
        up = agent.me.local(Vector(z=-1 if upside_down else 1))  # where "up" is in local coordinates
    target_angles = (
        math.atan2(local_target.z, local_target.x),  # angle required to pitch towards target
        math.atan2(local_target.y, local_target.x),  # angle required to yaw towards target
        math.atan2(up.y, up.z)  # angle required to roll upright
    )
    # Once we have the angles we need to rotate, we feed them into PD loops to determing the controller inputs
    agent.controller.steer = steerPD(target_angles[1], 0)
    agent.controller.pitch = steerPD(target_angles[0], agent.me.angular_velocity.y/4)
    agent.controller.yaw = steerPD(target_angles[1], -agent.me.angular_velocity.z/4)
    agent.controller.roll = steerPD(target_angles[2], agent.me.angular_velocity.x/4)
    # Returns the angles, which can be useful for other purposes
    return target_angles


def defaultThrottle(agent, target_speed, target_angles=None, local_target=None):
    # accelerates the car to a desired speed using throttle and boost
    car_speed = agent.me.local_velocity().x

    if not agent.me.airborne:
        if target_angles is not None and local_target is not None:
            turn_rad = turn_radius(abs(car_speed))
            agent.controller.handbrake = not agent.me.airborne and agent.me.velocity.magnitude() > 250 and (is_inside_turn_radius(turn_rad, local_target, sign(agent.controller.steer)) if abs(local_target.y) < turn_rad else abs(local_target.x) < turn_rad)

        angle_to_target = abs(target_angles[1])
        if target_speed < 0:
            angle_to_target = math.pi - angle_to_target
        if agent.controller.handbrake:
            if angle_to_target > 2.8:
                if abs(target_speed) > 950: target_speed = 950 * sign(target_speed)
                agent.controller.steer = sign(agent.controller.steer)
                agent.controller.handbrake = False
            else:
                agent.controller.steer = agent.controller.yaw

        t = target_speed - car_speed
        ta = throttle_acceleration(car_speed)
        agent.controller.throttle = cap(t / ta, -1, 1) if ta != 0 and (target_speed < 1410 or t < -ta/10) else sign(t if abs(t) > 117 else target_speed)

        if not agent.controller.handbrake:
            agent.controller.boost = angle_to_target < 0.5 and (t > ta / 30 + agent.boost_accel / 30 if target_speed < 1410 else t > agent.boost_accel / 30)

    return car_speed


def defaultDrive(agent, target_speed, local_target):
    target_angles = defaultPD(agent, local_target)
    velocity = defaultThrottle(agent, target_speed, target_angles, local_target)

    return target_angles, velocity


def throttle_acceleration(car_velocity_x):
    x = abs(car_velocity_x)
    if x >= 1410:
        return 0

    # use y = mx + b to find the throttle acceleration
    if x < 1400:
        return (-36 / 35) * x + 1600;

    x -= 1400;
    return -16 * x + 160;


def is_inside_turn_radius(turn_rad, local_target, steer_direction):
    # turn_rad is the turn radius
    local_target = local_target.flatten()
    circle = Vector(y=-steer_direction * turn_rad)

    return circle.dist(local_target) < turn_rad


def turn_radius(v):
    # v is the magnitude of the velocity in the car's forward direction
    if v == 0:
        return 0
    return 1.0 / curvature(v)


def curvature(v):
    # v is the magnitude of the velocity in the car's forward direction
    if 0 <= v < 500:
        return 0.0069 - 5.84e-6 * v
        
    if 500 <= v < 1000:
        return 0.00561 - 3.26e-6 * v

    if 1000 <= v < 1500:
        return 0.0043 - 1.95e-6 * v

    if 1500 <= v < 1750:
        return 0.003025 - 1.1e-7 * v

    if 1750 <= v < 2500:
        return 0.0018 - 0.4e-7 * v

    return 0


def in_field(point, radius):
    # determines if a point is inside the standard soccer field
    point = Vector(abs(point.x), abs(point.y), abs(point.z))
    return not (point.x > 4080 - radius or point.y > 5900 - radius or (point.x > 880 - radius and point.y > 5105 - radius) or (point.x > 2650 and point.y > -point.x + 8025 - radius))


def find_slope(shot_vector, car_to_target):
    # Finds the slope of your car's position relative to the shot vector (shot vector is y axis)
    # 10 = you are on the axis and the ball is between you and the direction to shoot in
    # -10 = you are on the wrong side
    # 1 = you're about 45 degrees offcenter
    d = shot_vector.dot(car_to_target)
    e = abs(shot_vector.cross(Vector(z=1)).dot(car_to_target))
    try:
        f = d / e
    except ZeroDivisionError:
        return 10*sign(d)
    return cap(f, -3, 3)


def quadratic(a, b, c):
    # Returns the two roots of a quadratic
    inside = (b*b) - (4*a*c)

    try:
        inside = math.sqrt(inside)
    except ValueError:
        return ()

    if inside < 0:
        return ()

    b = -b
    a = 2*a

    if inside == 0:
        return (b/a,)

    return ((b + inside)/a, (b - inside)/a)


def side(x):
    # returns -1 for blue team and 1 for orange team
    return (-1, 1)[x]


def sign(x):
    # returns the sign of a number, -1, 0, +1
    if x < 0:
        return -1

    if x > 0:
        return 1

    return 0


def steerPD(angle, rate):
    # A Proportional-Derivative control loop used for defaultPD
    return cap(((35*(angle+rate))**3)/10, -1, 1)


def lerp(a, b, t):
    # Linearly interpolate from a to b using t
    # For instance, when t == 0, a is returned, and when t is 1, b is returned
    # Works for both numbers and Vectors
    return (b - a) * t + a


def invlerp(a, b, v):
    # Inverse linear interpolation from a to b with value v
    # For instance, it returns 0 if v is a, and returns 1 if v is b, and returns 0.5 if v is exactly between a and b
    # Works for both numbers and Vectors
    return (v - a) / (b - a)


def send_comm(agent, msg):
    message = {
        "index": agent.index,
        "team": agent.team
    }
    msg.update(message)
    try:
        agent.matchcomms.outgoing_broadcast.put_nowait({
            "VirxERLU": msg
        })
    except Full:
        agent.print("Outgoing broadcast is full; couldn't send message")


def peek_generator(generator):
    try:
        return next(generator)
    except StopIteration:
        return


def almost_equals(x, y, threshold):
    return x - threshold < y and y < x + threshold


def point_inside_quadrilateral_2d(point, quadrilateral):
    # Point is a 2d vector
    # Quadrilateral is a tuple of 4 2d vectors, in either a clockwise or counter-clockwise order
    # See https://stackoverflow.com/a/16260220/10930209 for an explanation

    def area_of_triangle(triangle):
        return abs(sum((triangle[0].x * (triangle[1].y - triangle[2].y), triangle[1].x * (triangle[2].y - triangle[0].y), triangle[2].x * (triangle[0].y - triangle[1].y))) / 2)

    actual_area = area_of_triangle((quadrilateral[0], quadrilateral[1], point)) + area_of_triangle((quadrilateral[2], quadrilateral[1], point)) + area_of_triangle((quadrilateral[2], quadrilateral[3], point)) + area_of_triangle((quadrilateral[0], quadrilateral[3], point))
    quadrilateral_area = area_of_triangle((quadrilateral[0], quadrilateral[2], quadrilateral[1])) + area_of_triangle((quadrilateral[0], quadrilateral[2], quadrilateral[3]))

    # This is to account for any floating point errors
    return almost_equals(actual_area, quadrilateral_area, 0.001)


def perimeter_of_ellipse(a,b):
    return math.pi * (3*(a+b) - math.sqrt((3*a + b) * (a + 3*b)))


def dodge_impulse(agent):
    car_speed = agent.me.velocity.magnitude()
    impulse = 500 * (1 + 0.9 * (car_speed / 2300))
    dif = car_speed + impulse - 2300
    if dif > 0:
        impulse -= dif
    return impulse
