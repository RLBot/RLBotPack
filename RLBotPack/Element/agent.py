import os
import pickle
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical


class Agent:
    def __init__(self, state_space: int, action_categoricals: int, action_bernoullis: int):
        # Disable cpu parallelization
        torch.set_num_threads(1)
        
        self.state_space = state_space
        self.categoricals = action_categoricals
        self.bernoullis = action_bernoullis
        self.action_space = self.categoricals + self.bernoullis

        self.actor = Actor(state_space, self.categoricals, self.bernoullis)

        cur_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(cur_dir, 'model.p'), 'rb') as file:
            model = pickle.load(file)
        self.actor.load_state_dict(model)

    def act(self, state):
        state = torch.tensor(state, dtype=torch.float).view(-1, self.state_space)  # 1st dimension is batch number
        with torch.no_grad():
            probs = self.actor(state)

        probs_cat = probs[0]
        #dist = Categorical(probs_cat)
        #actions_cat = dist.sample()
        actions_cat = torch.argmax(probs_cat, dim=2)

        probs_ber = probs[1]
        #dist = Categorical(probs_ber)
        #actions_ber = dist.sample()
        actions_ber = torch.argmax(probs_ber, dim=2)

        actions = torch.cat([actions_cat, actions_ber], 1).numpy()
        return actions


class Actor(nn.Module):
    def __init__(self, input, categoricals, bernoullis):
        super(Actor, self).__init__()
        self.categoricals = categoricals
        self.bernoullis = bernoullis

        self.fc1 = nn.Linear(input, 256)
        self.fc2 = nn.Linear(256, 256)
        self.fc3 = nn.Linear(256, 256)
        self.fc4 = nn.Linear(256, 256)
        self.fc5 = nn.Linear(256, 256)
        self.cat_heads = nn.Linear(256, 3 * categoricals)
        self.ber_heads = nn.Linear(256, 2 * bernoullis)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.relu(self.fc4(x))
        x = F.relu(self.fc5(x))
        cat_output = F.softmax(self.cat_heads(x).view(-1, self.categoricals, 3), dim=2)
        ber_output = F.softmax(self.ber_heads(x).view(-1, self.bernoullis, 2), dim=2)
        return [cat_output, ber_output]
