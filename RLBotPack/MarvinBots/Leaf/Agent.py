import Bot
from rlbot.agents.base_agent import BaseAgent


class Leaf(BaseAgent):

    def get_output(self, packet):

        game = self.convert_packet_to_v3(packet)
        output = Bot.Process(self, game)

        return self.convert_output_to_v4(output)
