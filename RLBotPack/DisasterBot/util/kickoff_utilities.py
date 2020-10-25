import numpy as np
from skeleton.util.structure import GameData
from util.linear_algebra import norm, normalize, optimal_intercept_vector


def kickoff_decider(game_data: GameData) -> bool:
    if len(game_data.teammates) > 1:
        my_distance = np.linalg.norm(game_data.my_car.location - game_data.ball.location)
        for ally in game_data.teammates:
            if np.linalg.norm(ally[0][0] - game_data.ball.location) < my_distance:
                return False
    return True


def get_kickoff_position(position: np.array):
    # kickoff_locations = [[2048, 2560], [256, 3848], [0, 4608]]
    if abs(position[0]) >= 300:
        return 0  # wide diagonal
    elif abs(position[0]) > 5:
        return 1  # short diagonal
    else:
        return 2  # middle


def calc_target_dir(game_data: GameData, ball_location, ball_velocity):
    own_goal = game_data.own_goal.location - normalize(game_data.own_goal.direction) * 500
    opp_goal = game_data.opp_goal.location - normalize(game_data.opp_goal.direction) * 500

    relative_own = ball_location - own_goal
    relative_opp = opp_goal - ball_location

    opp_target_dir = optimal_intercept_vector(ball_location, ball_velocity, opp_goal,)

    return norm(relative_own) * normalize(opp_target_dir) + norm(relative_opp) * normalize(relative_own)
