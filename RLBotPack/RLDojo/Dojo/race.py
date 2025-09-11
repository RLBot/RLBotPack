import utils

import numpy as np
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState

class Race:
    def __init__(self):
        self.ball_state = None
        self.player_team = 0

        valid_start = False
        while not valid_start:
            # Place the ball in a random location
            x_loc = utils.random_between(-4096, 4096)
            y_loc = utils.random_between(-5120, 5120)
            z_loc = utils.random_between(90, 1954)
            ball_velocity = Vector3(0, 0, 0)

            # If the ball is too far from the floor and the sidewalls, try again
            dist_from_floor = abs(z_loc)
            dist_from_backwall = 5120 - abs(y_loc)
            dist_from_sidewall = 4096 - abs(x_loc)
            if dist_from_floor <  1000 or dist_from_backwall < 1000 or dist_from_sidewall < 1000:
                valid_start = True

        self.ball_state = BallState(Physics(location=Vector3(x_loc, y_loc, z_loc), velocity=ball_velocity))

        utils.sanity_check_objects([self.ball_state])

        
    def BallState(self):
        return self.ball_state