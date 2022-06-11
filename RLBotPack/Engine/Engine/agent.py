import numpy as np
from stable_baselines3 import PPO
import os, sys
import pathlib


class Agent:
    def __init__(self):
        _path = pathlib.Path(__file__).parent.resolve()
        custom_objects = {
            "lr_schedule": 0.00001,
            "clip_range": .02,
            "n_envs": 1,
            "device": "auto"
        }

        sys.path.append(_path)
        self.actor = PPO.load(str(_path) + '/engine', custom_objects=custom_objects)

    def act(self, state):
        action = self.actor.predict(state, deterministic=True)
        return np.array([value-1 if count < 5 else value for count, value in enumerate(action[0])]), None
