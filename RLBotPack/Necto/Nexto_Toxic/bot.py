import numpy as np
import torch
import random
import math

from datetime import datetime

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats
from rlgym_compat import GameState

import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
nexto_dir = parent

sys.path.append(nexto_dir)
sys.path.append(nexto_dir+'/Nexto')
from Nexto.agent import Agent
from Nexto.bot import Nexto


class ToxicNexto(Nexto):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        
        self.isToxic = True