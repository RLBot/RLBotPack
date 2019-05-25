from rlbot.agents.base_agent import BaseAgent

import core


class Cartana(BaseAgent):
    def initialize_agent(self):
        core.initialize(self)

    def get_output(self, packet):
        core.run(self, packet)
        return core.ctrl(self)
