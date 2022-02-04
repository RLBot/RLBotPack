from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.resolve()))
sys.path.append(str((Path(__file__).parent.parent / "Necto").resolve()))
from Necto.bot import Necto

sys.path.append(str((Path(__file__).parent.parent / "Bribblebot").resolve()))
from Bribblebot.bot import BribbleBot



class NotNecto(Necto, BribbleBot):
	
	def __init__(self, name, team, index):
		Necto.__init__(self, name, team, index)
		BribbleBot.__init__(self,name, team, index)

	def initialize_agent(self):
		Necto.initialize_agent(self)
		BribbleBot.initialize_agent(self)


	def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
		bribbleControls = BribbleBot.get_output(self, packet)
		if packet.game_ball.physics.location.x != 0 or packet.game_ball.physics.location.y != 0:
			return Necto.get_output(self, packet)

		return bribbleControls