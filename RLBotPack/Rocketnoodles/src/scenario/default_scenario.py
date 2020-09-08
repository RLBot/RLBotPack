from rlbot.utils.game_state_util import GameState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from typing import Optional
from scenario.base_scenario import BaseScenario


class DefaultScenario(BaseScenario):
    """For simulating in game scenarios. This scenario does not alter the game in any way.

     :param packet: Update packet with information about the current game state
     :type packet: GameTickPacket"""

    def __init__(self, packet: GameTickPacket):
        super().__init__(packet)

    def reset_upon_condition(self, packet: GameTickPacket) -> Optional[GameState]:
        """This is called every step and can be used to modify the state of the game when a condition is met.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket
         :return: The state of the game if the scenario reset condition was met, otherwise none.
         :rtype: GameState, optional
         """

    def reset(self) -> GameState:
        """Reinitialise this scenario when called. Is called upon initialization and when the reset conditions are met.

        :return: The freshly initialized game state for this scenario
        :rtype: GameState, optional
        """
