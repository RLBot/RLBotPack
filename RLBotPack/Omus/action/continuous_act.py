import numpy as np
from rlgym_compat import GameState


class ContinuousAction:
    """
        Simple continuous action space. Operates in the range -1 to 1, even for the binary actions which are converted back to binary later.
        This is for improved compatibility, stable baselines doesn't support tuple spaces right now.
    """

    def __init__(self):
        pass

    def get_action_space(self):
        raise NotImplementedError("We don't implement get_action_space to remove the gym dependency")

    def parse_actions(self, actions: np.ndarray, state: GameState) -> np.ndarray:
        actions = actions.reshape((-1, 8))

        actions[..., :5] = actions[..., :5].clip(-1, 1)
        # The final 3 actions handle are jump, boost and handbrake. They are inherently discrete so we convert them to either 0 or 1.
        actions[..., 5:] = actions[..., 5:] > 0

        return actions