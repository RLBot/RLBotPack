
from .vector_math import *
from collections import namedtuple

# Calculates stuff relating to tangents.
# Has a main() for debugging purposes.
# Note: "clockwise" in this file assumes X=right, Y=up
# !! If you want to keep thinking in Unreal coordinate system, think of the gamefield viewed from below, not above.

def tangent_point_line_circles(circle_center, circle_radius, point, clockwise):
    # Input - c circle object
    #         p point object of focus tangent line
    #         clockwise whether we are turning clockwise when spiralling from the circle to the tangent line
    # Return  tangent point on the circle 0 or 1
    # http://www.ambrsoft.com/TrigoCalc/Circles2/Circles2Tangent_.htm
    c_x, c_y = circle_center
    p_x, p_y = point
    c_r = circle_radius

    to_surface_dist = (p_x - c_x)**2 + (p_y - c_y)**2 - c_r**2  # point to circle surface distance

    if to_surface_dist >= 0:
        dis = sqrt(to_surface_dist)

        sign = 1 if clockwise else -1
        return Vec2(
            # TODO: Maybe there's amore nice vector expression.
            (c_r**2 * (p_x - c_x) + sign * c_r * (p_y - c_y) * dis) / ((p_x - c_x)**2 + (p_y - c_y)**2) + c_x,
            (c_r**2 * (p_y - c_y) - sign * c_r * (p_x - c_x) * dis) / ((p_x - c_x)**2 + (p_y - c_y)**2) + c_y,
        )
    else:
        # Point is inside the circle. No solutions.
        return None

def inner_tangent_points(center_0, radius_0, center_1, radius_1, clockwise):
    big_tangent_point = tangent_point_line_circles(center_0, radius_0 + radius_1, center_1, clockwise)
    if big_tangent_point is None:
        return None
    center_to_big_tangent_x = big_tangent_point - center_0
    normalized = center_to_big_tangent_x / (radius_0 + radius_1)
    return [
        center_0 + normalized * radius_0,  # point on circle_0
        center_1 - normalized * radius_1,  # point on circle_1
    ]

def outer_tangent_points(center_0, radius_0, center_1, radius_1, clockwise):
    if radius_0 == radius_1:  # Special case: Outer tangents never meet.
        if all(np.isclose(center_0, center_1)):
            right = Vec2(1.0, 0.0)  # Technically, we'd have infinite solutions. Let's pick one.
        else: # common case
            right = clockwise90degrees(normalize(center_1 - center_0))

        sign = -1 if clockwise else 1
        return [
           center_0 + (sign * radius_0) * right,
           center_1 + (sign * radius_1) * right,
        ]

    if radius_0 < radius_1:  # This changes the side on which the tangents meet
        clockwise = not clockwise
    intersection = (radius_1 * center_0 - radius_0 * center_1) / (radius_1 - radius_0)
    out = [
        tangent_point_line_circles(center_0, radius_0, intersection, clockwise),  # point on circle_0
        tangent_point_line_circles(center_1, radius_1, intersection, clockwise),  # point on circle_1
    ]
    if any(vec is None  for vec in out):
        return None
    return out

TangetPath = namedtuple('TangentPath', 'pos_0 pos_1 clockwise_0 clockwise_1 turn_center_0 turn_center_1 tangent_0 tangent_1')

def get_tangent_paths(pos_0, turn_radius_0, right_0, pos_1, turn_radius_1, right_1):
    # arguments:
    #   *_0 is the specification for the start
    #   *_1 is the specification for the end
    #   pos - Position
    #   turn_radius
    #   right - The normalized vector facing to the right of the velocity.
    # returns:
    #   list of TangetPaths, not sorted.

    turn_center_r_0 = pos_0 + turn_radius_0 * right_0
    turn_center_l_0 = pos_0 - turn_radius_0 * right_0
    turn_center_r_1 = pos_1 + turn_radius_1 * right_1
    turn_center_l_1 = pos_1 - turn_radius_1 * right_1

    configs = [
        # function                turn_center_0, clockwise_0,  turn_center_1,   clockwise_1
        (inner_tangent_points,  turn_center_l_0, False,        turn_center_r_1, True       ),
        (inner_tangent_points,  turn_center_r_0, True,         turn_center_l_1, False      ),
        (outer_tangent_points,  turn_center_l_0, False,        turn_center_l_1, False      ),
        (outer_tangent_points,  turn_center_r_0, True,         turn_center_r_1, True       ),
    ]
    tangent_pairs = [
        func(turn_center_0, turn_radius_0, turn_center_1, turn_radius_1, clockwise_0)
        for (func, turn_center_0, clockwise_0, turn_center_1, _) in configs
    ]

    options = []
    for config, tangents in zip(configs, tangent_pairs):
        if tangents is None:
            continue
        (_, turn_center_0, clockwise_0, turn_center_1, clockwise_1) = config
        options.append(TangetPath(
            pos_0,
            pos_1,
            clockwise_0,
            clockwise_1,
            turn_center_0,
            turn_center_1,
            tangents[0],
            tangents[1],
        ))
    return options


def get_length_of_arc_0(path):
    radius_0 = dist(path.turn_center_0, path.pos_0)
    return radius_0 * directional_angle(path.pos_0, path.turn_center_0, path.tangent_0, path.clockwise_0)
def get_length_of_arc_1(path):
    radius_1 = dist(path.turn_center_1, path.pos_1)
    return radius_1 * directional_angle(path.tangent_1, path.turn_center_1, path.pos_1, path.clockwise_1)
def get_length_of_straight(path):
    return dist(path.tangent_0, path.tangent_1)
def get_length_of_tangent_path(path):
    return get_length_of_arc_0(path) + get_length_of_straight(path) + get_length_of_arc_1(path)


if __name__ == '__main__':
    import tangents_visualizer
    tangents_visualizer.main()
