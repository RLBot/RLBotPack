import heapq
from collections import namedtuple

from numba import njit, from_dtype, f8, i8
from numba.types import Tuple, List, NamedTuple

from skeleton.util.structure.dtypes import dtype_full_boost
from util.physics.drive_1d_heuristic import state_at_distance_heuristic, state_at_distance_heuristic_vectorized

import numpy as np


Node = namedtuple("Node", ["time", "vel", "boost", "i", "prev"])
full_boost_type = from_dtype(dtype_full_boost)


@njit((full_boost_type[:], f8[:], i8, List(NamedTuple((f8, f8[::1], f8, i8, i8), Node))), cache=True)
def first_target(boost_pads: np.ndarray, target: np.ndarray, i, nodes):
    path = nodes[i]

    prev = nodes[path.prev]
    while prev.i != -2:
        path = prev
        prev = nodes[path.prev]

    if path.i == -1:
        return target
    return boost_pads[path.i]["location"][::1]


@njit((full_boost_type[:], f8[:], f8[:], i8, List(NamedTuple((f8, f8[::1], f8, i8, i8), Node))), cache=True)
def path_length(boost_pads: np.ndarray, start: np.ndarray, target: np.ndarray, i, nodes):
    path = nodes[i]

    length = 0

    location = target

    prev = nodes[path.prev]
    while prev.i != -2:
        prev_location = boost_pads[prev.i]["location"]
        length += np.linalg.norm(location - prev_location)
        path = prev
        location = prev_location

        prev = nodes[path.prev]

    prev_location = start
    length += np.linalg.norm(location - prev_location)

    return length


@njit((full_boost_type[:], f8[:], f8[:], f8[::1], f8, f8[::1]), cache=True)
def find_fastest_path(
    boost_pads: np.ndarray, start: np.ndarray, target: np.ndarray, vel: np.ndarray, boost: float, target_dir: np.ndarray
):
    time_end = state_at_distance_heuristic(target - start, vel, boost)[0]
    queue = [(time_end, 0)]
    nodes = [Node(0.0, vel, boost, -2, 0)]

    fix = True
    if np.dot(target - start, target_dir) >= 0 and not np.all(start == target):
        fix = False
    for pad in boost_pads:
        if np.dot(target - pad["location"], target_dir) >= 0 and not np.all(pad["location"] == target):
            fix = False
    if fix:
        target_dir = np.array([0.0, 0.0, 0.0])

    while True:
        index = heapq.heappop(queue)[1]
        state: Node = nodes[index]

        if state.i == -1:
            if np.dot(state.vel, target_dir) >= 0.0:
                return (
                    first_target(boost_pads, target, index, nodes),
                    path_length(boost_pads, start, target, index, nodes),
                )
            continue

        location = start
        if state.i != -2:
            location = boost_pads[state.i]["location"]

        for i in range(-1, boost_pads.shape[0]):
            pad_location = target
            if i != -1:
                pad_location = boost_pads[i]["location"]

            if np.all(pad_location == location):
                continue

            delta_time, vel, boost = state_at_distance_heuristic(pad_location - location, state.vel, state.boost)
            time = state.time + delta_time

            delta_time_end = 0.0
            if i != -1:
                pad_time = 10.0 if boost_pads[i]["is_full_boost"] else 4.0

                if boost_pads[i]["is_active"] or boost_pads[i]["timer"] + time >= pad_time:
                    pad_boost = 100.0 if boost_pads[i]["is_full_boost"] else 12.0
                    boost = min(boost + pad_boost, 100.0)

                delta_time_end = state_at_distance_heuristic(target - pad_location, vel, boost)[0]

            time_end = time + delta_time_end

            heapq.heappush(queue, (time_end, len(nodes)))
            nodes.append(Node(time, vel, boost, i, index))


def optional_boost_target(boost_pads: np.ndarray, start: np.ndarray, target: np.ndarray, vel: np.ndarray, boost: float):
    """Returns the original target or a boost location that will help to get to the target faster."""

    time_to_target = state_at_distance_heuristic(target - start, vel, boost)[0]

    time_at_pad, vel_at_pad, boost_at_pad = state_at_distance_heuristic_vectorized(
        boost_pads["location"] - start, [vel] * len(boost_pads), [boost] * len(boost_pads)
    )

    pad_recharge_time = np.where(boost_pads["is_full_boost"], 10, 4)
    valid_mask = (boost_pads["timer"] + time_at_pad >= pad_recharge_time) | boost_pads["is_active"]

    valid_boosts = boost_pads[valid_mask]
    time_at_pad = time_at_pad[valid_mask]
    vel_at_pad = vel_at_pad[valid_mask]
    boost_at_pad = boost_at_pad[valid_mask]

    if time_to_target <= np.min(time_at_pad):
        return target

    pad_boost = np.where(valid_boosts["is_full_boost"], 100, 12)
    boost_at_pad = np.minimum(boost_at_pad + pad_boost, 100)

    time_at_target, vel_at_target, boost_at_target = state_at_distance_heuristic_vectorized(
        target - valid_boosts["location"], vel_at_pad, boost_at_pad
    )

    time_at_target = time_at_target + time_at_pad
    min_pad_time_key = np.argmin(time_at_target)

    if time_to_target <= time_at_target[min_pad_time_key]:
        return target

    return valid_boosts[min_pad_time_key]["location"]


def main():
    """Testing for errors and performance"""

    from timeit import timeit
    from skeleton.test.skeleton_agent_test import SkeletonAgentTest

    agent = SkeletonAgentTest()
    agent.initialize_agent()

    boost_pads = agent.game_data.boost_pads[:5]

    boost_pads["timer"] = 0

    def test_function():
        boost_pads["location"] = np.random.rand(*boost_pads["location"].shape)
        boost_pads["is_active"] = np.random.rand(*boost_pads["is_active"].shape) > 0.5
        boost_pads["is_full_boost"] = np.random.rand(*boost_pads["is_full_boost"].shape) > 0.5

        my_loc = boost_pads["location"][3]
        target_loc = boost_pads["location"][4]
        vel = np.random.rand(3) / 1000
        target_dir = np.array([0, 1.0, 0])
        print(boost_pads, my_loc, target_loc, vel, target_dir)
        return find_fastest_path(boost_pads, my_loc, target_loc, vel, 50.0, target_dir)

    print(test_function())

    # def test_function():
    #     return optional_boost_target(boost_pads, my_loc, target_loc, vel, 50)
    #
    # print(test_function())

    fps = 120
    n_times = 100000
    time_taken = timeit(test_function, number=n_times)
    percentage = round(time_taken * fps / n_times * 100, 5)

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage} % of our time budget.")


if __name__ == "__main__":
    main()
