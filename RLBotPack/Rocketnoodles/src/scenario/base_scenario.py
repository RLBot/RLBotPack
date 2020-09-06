from abc import ABC, abstractmethod
from rlbot.utils.game_state_util import GameState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from typing import Optional


class BaseScenario(ABC):
    """Simulates in game scenarios. Used for testing.

     :param packet: Update packet with information about the current game state
     :type packet: GameTickPacket"""

    def __init__(self, packet: GameTickPacket):
        self.timer = 0.0
        self.prev_time = packet.game_info.seconds_elapsed
        self.delta_time = 0.0

    @abstractmethod
    def reset_upon_condition(self, packet: GameTickPacket) -> Optional[GameState]:
        """This is called every step and can be used to modify the state of the game when a condition is met.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket
         :return: The state of the game if the scenario reset condition was met, otherwise none.
         :rtype: GameState, optional
         """

    def _update_timer(self, packet: GameTickPacket):
        """Tracks the time for time based scenario events.

         :param packet: Update packet with information about the current game state
         :type packet: GameTickPacket"""
        self.delta_time = packet.game_info.seconds_elapsed - self.prev_time
        self.timer += self.delta_time
        self.prev_time = packet.game_info.seconds_elapsed

    @abstractmethod
    def reset(self) -> GameState:
        """Reinitialise this scenario when called. Is called upon initialization and when the reset conditions are met.

        :return: The freshly initialized game state for this scenario
        :rtype: GameState, optional
        """
