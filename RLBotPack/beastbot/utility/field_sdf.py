import math

from utility.info import Field
from utility.vec import Vec3, axis_to_rotation, vec_max, norm, max_comp, dot, normalize

ROUNDNESS = 300.0

SEMI_SIZE = Field.SIZE / 2
CORNER_SEMI_SIZE = Vec3(math.cos(math.pi / 4) * Field.CORNER_WALL_AX_INTERSECT,
                        math.cos(math.pi / 4) * Field.CORNER_WALL_AX_INTERSECT,
                        Field.HEIGHT / 2)
GOALS_SEMI_SIZE = Vec3(1786 / 2, Field.LENGTH / 2 + 880, Field.GOAL_HEIGHT / 2)

ROT_45_MAT = axis_to_rotation(Vec3(z=1) * math.pi / 4)


def sdf_wall_dist(point: Vec3) -> float:
    """
    Returns the distance to the nearest wall of using an SDF approximation.
    The result is negative if the point is outside the arena.
    """

    # SDF box https://www.youtube.com/watch?v=62-pRVZuS5c
    # SDF rounded corners https://www.youtube.com/watch?v=s5NGeUV2EyU

    ONES = Vec3(1, 1, 1)

    # Base cube
    base_q = abs(point - Vec3(z=Field.HEIGHT / 2)) - SEMI_SIZE + ONES * ROUNDNESS
    base_dist_outside = norm(vec_max(base_q, Vec3()))
    base_dist_inside = min(max_comp(base_q), 0)
    base_dist = base_dist_outside + base_dist_inside

    # Corners cube
    corner_q = abs((dot(ROT_45_MAT, point)) - Vec3(z=Field.HEIGHT / 2)) - CORNER_SEMI_SIZE + ONES * ROUNDNESS
    corner_dist_outside = norm(vec_max(corner_q, Vec3()))
    corner_dist_inside = min(max_comp(corner_q), 0)
    corner_dist = corner_dist_outside + corner_dist_inside

    # Intersection of base and corners
    base_corner_dist = max(base_dist, corner_dist) - ROUNDNESS

    # Goals cube
    goals_q = abs(point - Vec3(z=Field.GOAL_HEIGHT / 2)) - GOALS_SEMI_SIZE + ONES * ROUNDNESS
    goals_dist_outside = norm(vec_max(goals_q, Vec3()))
    goals_dist_inside = min(max_comp(goals_q), 0)
    goals_dist = goals_dist_outside + goals_dist_inside

    # Union with goals and invert result
    return -min(base_corner_dist, goals_dist)


def sdf_normal(point: Vec3) -> Vec3:
    """
    Returns the normalized gradient at the given point. At wall distance 0 this is the arena's surface normal.
    """
    # SDF normals https://www.iquilezles.org/www/articles/normalsSDF/normalsSDF.htm
    d = 0.0004
    return normalize(Vec3(
        sdf_wall_dist(point + Vec3(d, 0, 0)) - sdf_wall_dist(point - Vec3(d, 0, 0)),
        sdf_wall_dist(point + Vec3(0, d, 0)) - sdf_wall_dist(point - Vec3(0, d, 0)),
        sdf_wall_dist(point + Vec3(0, 0, d)) - sdf_wall_dist(point - Vec3(0, 0, d)),
    ))


def sdf_contains(point: Vec3) -> bool:
    return sdf_wall_dist(point) > 0
