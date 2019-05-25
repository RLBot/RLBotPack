from rlbot.agents.base_agent import BaseAgent

import Procedure
import Strategy
import Handling


class Stick(BaseAgent):

    def get_output(self, packet):

        Procedure.pre_process(self, packet)
        Strategy.plan(self)
        Handling.execute(self)
        Procedure.feedback(self)
        return self
