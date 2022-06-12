import numpy as np
from typing import List
from util.game_state import GameState, PlayerData


class Sequence:
    def is_valid(self, player: PlayerData, game_state: GameState) -> bool:
        raise NotImplementedError()

    def get_action(self, player: PlayerData, game_state: GameState, prev_action: np.ndarray) -> List:
        raise NotImplementedError()
