from __future__ import annotations

import math
from typing import TYPE_CHECKING
from typing import Union

from objects import Vector3

if TYPE_CHECKING:
    from hive import MyHivemind
    from objects import CarObject, BoostObject
    from routines import AerialShot, JumpShot, Aerial

# This file is for small utilities for math and movement

COAST_ACC = 525.0
BREAK_ACC = 3500
MIN_BOOST_TIME = 0.1


def backsolve(target: Vector3, car: CarObject, time: float, gravity: int = 650) -> Vector3:
    # Finds the acceleration required for a car to reach a target in a specific amount of time
    d = target - car.location
    dvx = ((d[0] / time) - car.velocity[0]) / time
    dvy = ((d[1] / time) - car.velocity[1]) / time
    dvz = (((d[2] / time) - car.velocity[2]) / time) + (gravity * time)
    return Vector3(dvx, dvy, dvz)


def cap(x: float, low: float, high: float) -> float:
    # caps/clamps a number between a low and high value
    return max(min(x, high), low)


def cap_in_field(drone: CarObject, target: Vector3):
    if abs(target[0]) > 893 - drone.hitbox.length:
        target[1] = cap(target[1], -5120 + drone.hitbox.length, 5120 - drone.hitbox.length)
    target[0] = cap(target[0], -893 + drone.hitbox.length, 893 - drone.hitbox.length) if abs(
        drone.location[1]) > 5120 - (drone.hitbox.length / 2) else cap(target[0], -4093 + drone.hitbox.length,
                                                                      4093 - drone.hitbox.length)

    return target


def defaultPD(drone: CarObject, local_target: Vector3, upside_down=False, up=None) -> []:
    # points the car towards a given local target.
    # Direction can be changed to allow the car to steer towards a target while driving backwards

    if up is None:
        up = drone.local(Vector3(0, 0, -1) if upside_down else Vector3(0, 0, 1))  # where "up" is in local coordinates
    target_angles = (
        math.atan2(local_target[2], local_target[0]),  # angle required to pitch towards target
        math.atan2(local_target[1], local_target[0]),  # angle required to yaw towards target
        math.atan2(up[1], up[2])  # angle required to roll upright
    )
    # Once we have the angles we need to rotate, we feed them into PD loops to determining the controller inputs
    drone.controller.steer = steerPD(target_angles[1], 0)
    drone.controller.pitch = steerPD(target_angles[0], drone.angular_velocity[1] / 4)
    drone.controller.yaw = steerPD(target_angles[1], -drone.angular_velocity[2] / 4)
    drone.controller.roll = steerPD(target_angles[2], drone.angular_velocity[0] / 4)
    # Returns the angles, which can be useful for other purposes
    return target_angles


def defaultThrottle(drone: CarObject, target_speed: float, target_angles=None, local_target=None) -> float:
    # accelerates the car to a desired speed using throttle and boost
    car_speed = drone.local_velocity()[0]

    if not drone.airborne:
        if target_angles is not None and local_target is not None:
            turn_rad = turn_radius(abs(car_speed))
            drone.controller.handbrake = not drone.airborne and drone.velocity.magnitude() > 250 and (
                is_inside_turn_radius(turn_rad, local_target, sign(drone.controller.steer)) if abs(
                    local_target[1]) < turn_rad else abs(local_target[0]) < turn_rad)

        angle_to_target = abs(target_angles[1])
        if target_speed < 0:
            angle_to_target = math.pi - angle_to_target
        if drone.controller.handbrake:
            if angle_to_target > 2.6:
                drone.controller.steer = sign(drone.controller.steer)
                drone.controller.handbrake = False
            else:
                drone.controller.steer = drone.controller.yaw

        t = target_speed - car_speed
        ta = throttle_acceleration(abs(car_speed)) * drone.delta_time
        if ta != 0:
            drone.controller.throttle = cap(t / ta, -1, 1)
        elif sign(target_speed) * t > -COAST_ACC * drone.delta_time:
            drone.controller.throttle = sign(target_speed)
        elif sign(target_speed) * t <= -COAST_ACC * drone.delta_time:
            drone.controller.throttle = sign(t)

        if not drone.controller.handbrake:
            drone.controller.boost = t - ta >= drone.boost_accel * MIN_BOOST_TIME

    return car_speed


def defaultDrive(drone: CarObject, target_speed, local_target):
    target_angles = defaultPD(drone, local_target)
    velocity = defaultThrottle(drone, target_speed, target_angles, local_target)

    return target_angles, velocity


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
    circle = Vector3(0, -steer_direction * turn_rad, 0)

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


def in_field(point: Vector3, radius: float) -> bool:
    # determines if a point is inside the standard soccer field
    point = Vector3(abs(point[0]), abs(point[1]), abs(point[2]))
    if point[0] > 4080 - radius:
        return False
    elif point[1] > 5900 - radius:
        return False
    elif point[0] > 880 - radius and point[1] > 5105 - radius:
        return False
    elif point[0] > 2650 and point[1] > -point[0] + 8025 - radius:
        return False
    return True


def find_slope(shot_vector: Vector3, car_to_target: Vector3) -> float:
    # Finds the slope of your car's position relative to the shot vector (shot vector is y axis)
    # 10 = you are on the axis and the ball is between you and the direction to shoot in
    # -10 = you are on the wrong side
    # 1 = you're about 45 degrees offcenter
    d = shot_vector.dot(car_to_target)
    e = abs(shot_vector.cross(Vector3(0, 0, 1)).dot(car_to_target))
    try:
        f = d / e
    except ZeroDivisionError:
        return 10 * sign(d)
    return cap(f, -3, 3)


def post_correction(ball_location: Vector3, left_target: Vector3, right_target: Vector3) -> (Vector3, Vector3, bool):
    # this function returns target locations that are corrected to account for the ball's radius
    # If the left and right post swap sides, a goal cannot be scored
    ball_radius = 120  # We purposly make this a bit larger so that our shots have a higher chance of success
    goal_line_perp = (right_target - left_target).cross((0, 0, 1))
    left = left_target + ((left_target - ball_location).normalize().cross((0, 0, -1)) * ball_radius)
    right = right_target + ((right_target - ball_location).normalize().cross((0, 0, 1)) * ball_radius)
    left = left_target if (left - left_target).dot(goal_line_perp) > 0.0 else left
    right = right_target if (right - right_target).dot(goal_line_perp) > 0.0 else right
    swapped = True if (left - ball_location).normalize().cross((0, 0, 1)).dot(
        (right - ball_location).normalize()) > -0.1 else False
    return left, right, swapped


def quadratic(a: float, b: float, c: float) -> (float, float):
    # Returns the two roots of a quadratic
    inside = math.sqrt((b * b) - (4 * a * c))
    if a != 0:
        return (-b + inside) / (2 * a), (-b - inside) / (2 * a)
    else:
        return -1, -1


def sign(x: float) -> float:
    # returns the sign of a number, -1, 0, +1
    if x < 0.0:
        return -1
    elif x > 0.0:
        return 1
    else:
        return 0.0


def steerPD(angle: float, rate: float) -> float:
    # A Proportional-Derivative control loop used for defaultPD
    return cap(((35 * (angle + rate)) ** 3) / 10, -1.0, 1.0)


def lerp(a: float, b: float, t: float) -> float:
    # Linearly interpolate from a to b using t
    # For instance, when t == 0, a is returned, and when t == 1, b is returned
    # Works for both numbers and Vector3s
    return (b - a) * t + a


def invlerp(a: float, b: float, v: float) -> float:
    # Inverse linear interpolation from a to b with value v
    # For instance, it returns 0 if v == a, and returns 1 if v == b, and returns 0.5 if v is exactly between a and b
    # Works for both numbers and Vector3s
    return (v - a) / (b - a)


def closest_boost(agent: MyHivemind, location: Vector3, return_distance=False) -> \
        Union[BoostObject, (BoostObject, float)]:
    large_boosts = [boost for boost in agent.boosts if boost.large and boost.active]
    if len(large_boosts) == 0:
        return None
    closest = large_boosts[0]
    closest_distance = (closest.location - location).magnitude()
    for boost in large_boosts:
        boost_distance = (boost.location - location).magnitude()
        if boost_distance < closest_distance:
            closest = boost
            closest_distance = boost_distance
    if return_distance:
        return closest, closest_distance
    else:
        return closest


def closest_foe(agent: MyHivemind, location: Vector3, return_distance=False) -> \
        Union[CarObject, (CarObject, float)]:
    closest = agent.foes[0]
    closest_distance = (closest.location - location).magnitude()
    for foe in agent.foes:
        foe_distance = (foe.location - location).magnitude()
        if foe_distance < closest_distance:
            closest = foe
            closest_distance = foe_distance
    if return_distance:
        return closest, closest_distance
    else:
        return closest


def shot_valid(agent: MyHivemind, shot: Union[AerialShot, JumpShot, Aerial], threshold: float = 45) -> bool:
    # Returns True if the ball is still where the shot anticipates it to be
    # First finds the two closest slices in the ball prediction to shot's intercept_time
    # threshold controls the tolerance we allow the ball to be off by
    slices = agent.get_ball_prediction_struct().slices
    soonest = 0
    latest = len(slices) - 1
    while len(slices[soonest:latest + 1]) > 2:
        midpoint = (soonest + latest) // 2
        if slices[midpoint].game_seconds > shot.intercept_time:
            latest = midpoint
        else:
            soonest = midpoint
    # preparing to interpolate between the selected slices
    dt = slices[latest].game_seconds - slices[soonest].game_seconds
    time_from_soonest = shot.intercept_time - slices[soonest].game_seconds
    slopes = (Vector3(slices[latest].physics.location) - Vector3(slices[soonest].physics.location)) * (1 / dt)
    # Determining exactly where the ball will be at the given shot's intercept_time
    predicted_ball_location = Vector3(slices[soonest].physics.location) + (slopes * time_from_soonest)
    # Comparing predicted location with where the shot expects the ball to be
    return (shot.ball_location - predicted_ball_location).magnitude() < threshold


def distance(a: Vector3, b: Vector3) -> float:
    return (a - b).magnitude()


def dodge_impulse(drone: CarObject) -> float:
    car_speed = drone.velocity.magnitude()
    impulse = 500 * (1 + 0.9 * (car_speed / 2300))
    dif = car_speed + impulse - 2300
    if dif > 0:
        impulse -= dif
    return impulse

def side(x):
    # returns -1 for blue team and 1 for orange team
    return (-1, 1)[x]