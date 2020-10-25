import numpy as np


def closest_available_boost(my_loc: np.ndarray, boost_pads: np.ndarray) -> np.ndarray:
    """Returns the closest available boost pad to my_loc"""

    distances = np.linalg.norm(boost_pads["location"] - my_loc[None, :], axis=1)
    recharge_time = np.where(boost_pads["is_full_boost"], 10, 4)
    available = boost_pads["is_active"] | (distances / 2300 > recharge_time - boost_pads["timer"])

    available_distances = distances[available]
    if len(available_distances) > 0:
        available_boost = boost_pads[available]
        closest_available_index = np.argmin(available_distances)
        return available_boost[closest_available_index]
    else:
        return None


def available_boost_pads(my_loc: np.ndarray, boost_pads: np.ndarray) -> np.ndarray:
    """Returns a list of boost_pads that are active when we reach them."""
    distances = np.linalg.norm(boost_pads["location"] - my_loc[None, :], axis=1)
    recharge_time = np.where(boost_pads["is_full_boost"], 10, 4)
    available = boost_pads["is_active"] | (distances / 2300 > recharge_time - boost_pads["timer"])
    return boost_pads[available]


def main():
    """Testing for errors and performance"""

    from timeit import timeit
    from rlbot.utils.structures.game_data_struct import GameTickPacket
    from skeleton.test.skeleton_agent_test import SkeletonAgentTest, MAX_BOOSTS

    agent = SkeletonAgentTest()
    game_tick_packet = GameTickPacket()
    game_tick_packet.num_boost = MAX_BOOSTS
    agent.initialize_agent()

    def test_function():
        return closest_available_boost(agent.game_data.my_car.location, agent.game_data.boost_pads)

    test_function()

    fps = 120
    n_times = 10000
    time_taken = timeit(test_function, number=n_times)
    percentage = time_taken * fps / n_times * 100

    print(f"Took {time_taken} seconds to run {n_times} times.")
    print(f"That's {percentage:.5f} % of our time budget.")


if __name__ == "__main__":
    main()
