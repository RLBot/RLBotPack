
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket


class State:

    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.controller = SimpleControllerState()