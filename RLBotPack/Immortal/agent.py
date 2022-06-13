import math
import os

import numpy as np
import torch
import torch.nn.functional as F
from torch.distributions import Categorical

from action.actionparser import ImmortalAction


def get_action_distribution(obs, actor):
    if isinstance(obs, np.ndarray):
        obs = torch.from_numpy(obs).float()
    elif isinstance(obs, tuple):
        obs = tuple(o if isinstance(o, torch.Tensor) else torch.from_numpy(o).float() for o in obs)

    out = actor(obs)

    if isinstance(out, torch.Tensor):
        out = (out,)

    max_shape = max(o.shape[-1] for o in out)
    logits = torch.stack(
        [
            l
            if l.shape[-1] == max_shape
            else F.pad(l, pad=(0, max_shape - l.shape[-1]), value=float("-inf"))
            for l in out
        ],
        dim=1
    )

    return Categorical(logits=logits)


def sample_action(
        distribution: Categorical,
        deterministic=None
):
    if deterministic:
        action_indices = torch.argmax(distribution.logits, dim=-1)
    else:
        action_indices = distribution.sample()

    return action_indices



def env_compatible(action):
    if isinstance(action, torch.Tensor):
        action = action.numpy()
    return action


class Agent:
    def __init__(self):
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.actor = torch.jit.load(os.path.join(cur_dir, "jit.pt"))
        torch.set_num_threads(1)
        self.action_parser = ImmortalAction()

    def act(self, state):
        with torch.no_grad():
            all_actions = []
            dist = get_action_distribution(state, self.actor)
            action_indices = sample_action(dist, deterministic=True)[0]
            actions = env_compatible(action_indices)

            all_actions.append(actions)
            all_actions = np.array(all_actions)

        return all_actions
