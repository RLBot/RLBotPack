from queue import Full

from util.agent import Vector, VirxERLU, math

COAST_ACC = 525.0
BRAKE_ACC = 3500
MIN_BOOST_TIME = 0.1
REACTION_TIME = 0.04

BRAKE_COAST_TRANSITION = -(0.45 * BRAKE_ACC + 0.55 * COAST_ACC)
COASTING_THROTTLE_TRANSITION = -0.5 * COAST_ACC
MIN_WALL_SPEED = -0.5 * BRAKE_ACC


def cap(x, low, high):
    # caps/clamps a number between a low and high value
    return low if x < low else (high if x > high else x)


def cap_in_field(agent: VirxERLU, target):
    if abs(target.x) > 893 - agent.me.hitbox.length:
        target.y = cap(target.y, -5120 + agent.me.hitbox.length, 5120 - agent.me.hitbox.length)
    target.x = cap(target.x, -893 + agent.me.hitbox.length, 893 - agent.me.hitbox.length) if abs(agent.me.location.y) > 5120 - (agent.me.hitbox.length / 2) else cap(target.x, -4093 + agent.me.hitbox.length, 4093 - agent.me.hitbox.length)

    return target


def defaultPD(agent: VirxERLU, local_target, upside_down=False, up=None):
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


def defaultThrottle(agent: VirxERLU, target_speed, target_angles=None, local_target=None):
    # accelerates the car to a desired speed using throttle and boost
    car_speed = agent.me.forward.dot(agent.me.velocity)

    if agent.me.airborne:
        return car_speed

    if target_angles is not None and local_target is not None:
        turn_rad = turn_radius(abs(car_speed))
        agent.controller.handbrake = not agent.me.airborne and agent.me.velocity.magnitude() > 600 and (is_inside_turn_radius(turn_rad, local_target, sign(agent.controller.steer)) if abs(local_target.y) < turn_rad or car_speed > 1410 else abs(local_target.x) < turn_rad)
        
        agent.controller.steer = agent.controller.yaw

    # Thanks to Chip's RLU speed controller for this
    # https://github.com/samuelpmish/RLUtilities/blob/develop/src/mechanics/drive.cc#L182
    # I had to make a few changes because it didn't play very nice with driving backwards

    t = target_speed - car_speed
    acceleration = t / REACTION_TIME
    if car_speed < 0: acceleration *= -1  # if we're going backwards, flip it so it thinks we're driving forwards

    brake_coast_transition = BRAKE_COAST_TRANSITION
    coasting_throttle_transition = COASTING_THROTTLE_TRANSITION
    throttle_accel = throttle_acceleration(car_speed)
    throttle_boost_transition = 1 * throttle_accel + 0.5 * agent.boost_accel

    if agent.me.up.z < 0.7:
        brake_coast_transition = coasting_throttle_transition = MIN_WALL_SPEED

    # apply brakes when the desired acceleration is negative and large enough
    if acceleration <= brake_coast_transition:
        agent.controller.throttle = -1

    # let the car coast when the acceleration is negative and small
    elif brake_coast_transition < acceleration and acceleration < coasting_throttle_transition:
        pass

    # for small positive accelerations, use throttle only
    elif coasting_throttle_transition <= acceleration and acceleration <= throttle_boost_transition:
        agent.controller.throttle = 1 if throttle_accel == 0 else cap(acceleration / throttle_accel, 0.02, 1)

    # if the desired acceleration is big enough, use boost
    elif throttle_boost_transition < acceleration:
        agent.controller.throttle = 1
        # if not agent.controller.handbrake:
        #     if t > 0 and angle_to_target < 1:
        #         agent.controller.boost = True  # don't boost when we need to lose speed, we we're using handbrake, or when we aren't facing the target

    if car_speed < 0:
        agent.controller.throttle *= -1  # earlier we flipped the sign of the acceleration, so we have to flip the sign of the throttle for it to be correct

    return car_speed


def defaultDrive(agent: VirxERLU, target_speed, local_target):
    target_angles = defaultPD(agent, local_target)
    velocity = defaultThrottle(agent, target_speed, target_angles, local_target)

    return target_angles, velocity


def get_max_speed_from_local_point(point):
    turn_rad = max(abs(point.x), abs(point.y))
    return curvature_to_velocity(1 / turn_rad)


def curvature_to_velocity(curve):
    curve = cap(curve, 0.00088, 0.0069)
    if 0.00088 <= curve <= 0.00110:
        u = (curve - 0.00088) / (0.00110 - 0.00088)
        return lerp(2300, 1750, u)

    if 0.00110 <= curve <= 0.00138:
        u = (curve - 0.00110) / (0.00138 - 0.00110)
        return lerp(1750, 1500, u)

    if 0.00138 <= curve <= 0.00235:
        u = (curve - 0.00138) / (0.00235 - 0.00138)
        return lerp(1500, 1000, u)

    if 0.00235 <= curve <= 0.00398:
        u = (curve - 0.00235) / (0.00398 - 0.00235)
        return lerp(1000, 500, u)

    if 0.00398 <= curve <= 0.0069:
        u = (curve - 0.00398) / (0.0069 - 0.00398)
        return lerp(500, 0, u)


def throttle_acceleration(car_velocity_x):
    x = abs(car_velocity_x)
    if x >= 1410:
        return 0

    # use y = mx + b to find the throttle acceleration
    if x < 1400:
        return (-36 / 35) * x + 1600

    x -= 1400
    return -16 * x + 160


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


def send_comm(agent: VirxERLU, msg):
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


def ray_intersects_with_line(origin, direction, point1, point2):
    v1 = origin - point1
    v2 = point2 - point1
    v3 = Vector(-direction.y, direction.x)
    v_dot = v2.dot(v3)

    t1 = v2.cross(v1).magnitude() / v_dot

    if t1 < 0:
        return

    t2 = v1.dot(v3) / v_dot

    if 0 <= t1 and t2 <= 1:
        return t1


def ray_intersects_with_circle(origin, direction, center, radius):
    L = center - origin
    tca = L.dot(direction)

    if tca < 0:
        return False

    d2 = L.dot(L) - tca * tca

    if d2 > radius:
        return False

    thc = math.sqrt(radius * radius - d2)
    t0 = tca - thc
    t1 = tca + thc

    return t0 > 0 or t1 > 0


def min_non_neg(x, y):
    return x if (x < y and x >= 0) or (y < 0 and x >= 0) else y


# solve for x
# y = a(x - h)^2 + k
# y - k = a(x - h)^2
# (y - k) / a = (x - h)^2
# sqrt((y - k) / a) = x - h
# sqrt((y - k) / a) + h = x
def vertex_quadratic_solve_for_x_min_non_neg(a, h, k, y):
    try:
        v_sqrt = math.sqrt((y - k) / a)
    except ValueError:
        return 0
    return min_non_neg(v_sqrt + h, -v_sqrt + h)


def get_landing_time(fall_distance, falling_time_until_terminal_velocity, falling_distance_until_terminal_velocity, terminal_velocity, k, h, g):
    return vertex_quadratic_solve_for_x_min_non_neg(g, h, k, fall_distance) if (fall_distance * sign(-g) <= falling_distance_until_terminal_velocity * sign(-g)) else falling_time_until_terminal_velocity + ((fall_distance - falling_distance_until_terminal_velocity) / terminal_velocity)


def find_landing_plane(l: Vector, v: Vector, g: float):
    if abs(l.y) >= 5120 or (v.x == 0 and v.y == 0 and g == 0):
        return 5

    times = [ -1, -1, -1, -1, -1, -1 ] #  side_wall_pos, side_wall_neg, back_wall_pos, back_wall_neg, ceiling, floor

    if v.x != 0:
        times[0] = (4080 - l.x) / v.x
        times[1] = (-4080 - l.x) / v.x

    if v.y != 0:
        times[2] = (5110 - l.y) / v.y
        times[3] = (-5110 - l.y) / v.y

    if g != 0:
        # this is the vertex of the equation, which also happens to be the apex of the trajectory
        h = v.z / -g # time to apex
        k = v.z * v.z / -g # vertical height at apex

        # a is the current gravity... because reasons
        # a = g

        climb_dist = -l.z

        # if the gravity is inverted, the the ceiling becomes the floor and the floor becomes the ceiling...
        if g < 0:
            climb_dist += 2030
            if k >= climb_dist:
                times[4] = vertex_quadratic_solve_for_x_min_non_neg(g, h, k, climb_dist)
        elif g > 0:
            climb_dist += 20
            if k <= climb_dist:
                times[5] = vertex_quadratic_solve_for_x_min_non_neg(g, h, k, climb_dist)

        # this is necessary because after we reach our terminal velocity, the equation becomes linear (distance_remaining / terminal_velocity)
        terminal_velocity = (2300 - v.flatten().magnitude()) * sign(g)
        falling_time_until_terminal_velocity = (terminal_velocity - v.z) / g
        falling_distance_until_terminal_velocity = v.z * falling_time_until_terminal_velocity + -g * (falling_time_until_terminal_velocity * falling_time_until_terminal_velocity) / 2.

        fall_distance = -l.z
        if g < 0:
            times[5] = get_landing_time(fall_distance + 20, falling_time_until_terminal_velocity, falling_distance_until_terminal_velocity, terminal_velocity, k, h, g)
        else:
            times[4] = get_landing_time(fall_distance + 2030, falling_time_until_terminal_velocity, falling_distance_until_terminal_velocity, terminal_velocity, k, h, g)

    return times.index(min(item for item in times if item >= 0))
