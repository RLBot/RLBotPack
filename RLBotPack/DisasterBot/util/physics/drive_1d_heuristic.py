import numpy as np
from numba import njit, f8

from util.physics.drive_1d_distance import state_at_distance, state_at_distance_vectorized


@njit((f8[:], f8[:], f8), cache=True)
def state_at_distance_heuristic(rel_loc, vel, boost):
    distance = np.linalg.norm(rel_loc)
    direction = rel_loc / np.maximum(distance, 1e-9)
    vel_to_target = np.dot(vel, direction)
    time, vel, boost = state_at_distance(distance, vel_to_target, boost)
    return time, vel * direction, boost


def state_at_distance_heuristic_vectorized(rel_loc, vel, boost):
    distance = np.linalg.norm(rel_loc, axis=1)
    direction = rel_loc / np.maximum(distance, 1e-9)[:, None]
    vel_to_target = np.inner(vel, direction).diagonal()

    dist_arg = np.array(distance, dtype=np.float64)
    vel_arg = np.array(vel_to_target, dtype=np.float64)
    boost_arg = np.array(boost, dtype=np.float64)

    time, vel, boost = state_at_distance_vectorized(dist_arg, vel_arg, boost_arg)
    return time, vel[:, None] * direction, boost
