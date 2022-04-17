from typing import List
from .sequence import Sequence
from util.game_state import GameState, PlayerData

import numpy as np


class Speedflip(Sequence):
    def __init__(self, player: PlayerData):
        self.state = 'align'
        self.initial_player = player

        car = player.car_data if player.team_num == 0 else player.inverted_car_data

        self.direction = 1 if car.position[0] > 0 else -1
        self.initial_angle = np.pi / 16
        self.drive_distance = 0
        self.valid_distance = 600

        if abs(car.position[0]) < 25:
            self.yaw_strength = 1
            self.drive_distance = 290
            self.initial_angle = np.pi / 22
        elif abs(car.position[0]) < 500:
            self.yaw_strength = 0.6
            self.drive_distance = 330
            self.direction = -self.direction
        else:
            self.yaw_strength = 0.4
            self.drive_distance = 240

    def is_valid(self, player: PlayerData, game_state: GameState) -> bool:
        ball = game_state.ball if player.team_num == 0 else game_state.inverted_ball
        car = player.car_data if player.team_num == 0 else player.inverted_car_data
        ball_dist = np.linalg.norm(ball.position - car.position)
        return self.state != 'done' and ball_dist > self.valid_distance

    def get_action(self, player: PlayerData, game_state: GameState, prev_action: np.ndarray) -> List:
        initial_car = self.initial_player.car_data if player.team_num == 0 else self.initial_player.inverted_car_data
        car = player.car_data if player.team_num == 0 else player.inverted_car_data

        if self.state == 'align':
            angle = np.arccos(np.dot(car.forward(), initial_car.forward()))
            if angle < self.initial_angle:
                return [1, -self.direction, 0, 0, 0, 0, 1, 0]
            else:
                self.state = 'drive'

        if self.state == 'drive':
            distance = np.linalg.norm(car.position - initial_car.position)
            if distance < self.drive_distance:
                return [1, 0, 0, 0, 0, 0, 1, 0]
            else:
                self.state = 'first_jump'

        if self.state == 'first_jump':
            self.state = 'start_flip'
            return [1, 0, 0, 0, 0, 1, 1, 0]

        if self.state == 'start_flip':
            if player.on_ground:
                # release jump
                return [1, 0, 0, 0, self.direction, 0, 1, 0]
            else:
                # dodge
                self.state = 'cancel_flip'
                return [1, 0, -1, 0, self.direction, 1, 1, 0]

        if self.state == 'cancel_flip':
            boost = 1 if np.linalg.norm(car.linear_velocity) < 2295 else 0
            print('Boost: {} - Speed: {}'.format(boost, np.linalg.norm(car.linear_velocity)))
            if not player.on_ground:
                return [1, 0, 1, self.yaw_strength * self.direction, self.direction, 0, boost, 0]
            else:
                # landed
                self.state = 'done'
                return [1, 0, 0, 0, 0, 0, 1, 0]

        print("Element - this shouldn't be printed")
        raise AssertionError('State machine didn\'t return a value')
