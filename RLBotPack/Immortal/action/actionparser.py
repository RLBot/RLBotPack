from typing import Any

import numpy as np


class ImmortalAction:
    def __init__(self):
        super().__init__()
        self._lookup_table = self._make_lookup_table()

    @staticmethod
    def _make_lookup_table():
        actions = []
        # Ground
        for throttle in (-1, 0, 1):
            for steer in (-1, 0, 1):
                for boost in (0, 1):
                    for handbrake in (0, 1):
                        if boost == 1 and throttle != 1:
                            continue
                        actions.append([throttle or boost, steer, 0, steer, 0, 0, boost, handbrake])
        # Aerial
        for pitch in (-1, 0, 1):
            for yaw in (-1, 0, 1):
                for roll in (-1, 0, 1):
                    for jump in (0, 1):
                        for boost in (0, 1):
                            if pitch == roll == jump == 0:
                                continue
                            actions.append([boost, yaw, pitch, yaw, roll, jump, boost, 1])
        actions = np.array(actions)
        return actions

    def parse_actions(self, actions: Any) -> np.ndarray:
        return self._lookup_table[np.array(actions, dtype=np.float32).squeeze().astype(int)]