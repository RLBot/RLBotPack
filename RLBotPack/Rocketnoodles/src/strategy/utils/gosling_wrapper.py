from gosling.objects import GoslingAgent
from strategy.base_ccp import SharedInfo
from typing import List, Tuple, Optional


class GoslingAgentWrapper(GoslingAgent, SharedInfo):
    """"Gosling wrapper used to enable the use of Gosling routines together with the CCP model.

    :param name: The name of the drone as given by RLBOT.
    :param team: The team of the drone as given by RLBOT (0 for blue or 1 for orange).
    :param index: The unique index of the drone as given by RLBOT."""

    def __init__(self, name: str, team: int, index: int):
        self.flush: bool = None
        self.stack: List = None

        self.index = index
        super(GoslingAgentWrapper, self).__init__(name, team, index)
        self.initialize_agent()

    def get_field_info(self):
        """"Returns the field info from the world model.

        :returns: Field info as if retrieved by a real RLBOT agent.
        """
        return self.world.field_info

    def update(self, routine) -> Tuple[Optional[List], bool, bool]:
        """"Update this wrapper and obtain the controls for the current routine.

        :return: The stack containing all newly obtained routines and the current one.
        :rtype: list
        :return: Done flag if the routine stack is empty.
        :rtype: bool
        :return: Whether the agents actions have been flushed.
        :rtype: bool
        """

        # Reset controller
        self.controller.__init__()
        self.flush = False

        # Get ready, then preprocess
        if not self.ready:
            self.get_ready(self.world.packet)
        self.preprocess(self.world.packet)

        # Create a fake stack and run. Run empties the stack when the routine finishes, resulting in done = True.
        self.stack = [routine]
        self.stack[-1].run(self)

        if len(self.stack) > 0:
            return self.stack, len(self.stack) == 0, self.flush
        else:
            return None, len(self.stack) == 0, self.flush

    def flush_actions(self):
        """ Removes all the items from the stack"""
        self.stack = []
        self.flush = True
