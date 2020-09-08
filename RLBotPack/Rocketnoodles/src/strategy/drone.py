from strategy.base_ccp import SharedInfo, BasePlayer
from strategy.utils import GoslingAgentWrapper
from gosling.objects import GoslingAgent, boost_object
from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.agents.base_agent import SimpleControllerState
from typing import List, Type
from world.components import Car


class Drone(SharedInfo):
    """"The drone class that keeps track of and updates the controls of this drone for each timestep.

    :param name: The name of the drone as given by RLBOT.
    :param team: The team of the drone as given by RLBOT (0 for blue or 1 for orange).
    :param index: The unique index of the drone as given by RLBOT."""

    def __init__(self, name: str, team: int, index: int):
        super().__init__()

        # Default drone properties
        self.name: str = name
        self.team: int = team
        self.index: int = index

        # A list that acts as the routines stack
        self.player_stack: List = []

        self.controller: SimpleControllerState = SimpleControllerState()
        self.gosling_wrapper: GoslingAgentWrapper = GoslingAgentWrapper(name, team, index)

    def step(self) -> bool:
        """"Step function for the drone class. Sets the controls for the current step.

        :return: Done flag if the routine stack is empty.
        :rtype: bool
        """

        # run the routine on the end of the stack
        if len(self.player_stack) > 0:
            current_routine = self.player_stack[-1]

            # Switch for gosling wrapper and CCP style player movement.
            if issubclass(type(current_routine), BasePlayer):
                done = self._step_base_player(current_routine)
            else:
                done = self._step_gosling(current_routine)

            if done:
                self.player_stack.pop()

        return len(self.player_stack) == 0

    def assign(self, routine):
        """"Assign a new player routine to this drone by pushing it on the stack.

        :param routine: Either a CCP BasePlayer instance or a Gosling routine.
        """
        self.player_stack.append(routine)

    def get_player_input(self) -> PlayerInput:
        """"Get the current controls from the drone.

        :return: Current controls for this car.
        :rtype: PlayerInput
        """

        # Throw error if no controls were set.
        if self.controller is None:
            RuntimeError(f"Did not set the controls for drone {self.index}")

        # PlayerInput mapping
        player_input = PlayerInput()
        player_input.throttle = self.controller.throttle  # -1 for full reverse, 1 for full forward
        player_input.steer = self.controller.steer  # -1 for full left, 1 for full right
        player_input.pitch = self.controller.pitch  # -1 for nose down, 1 for nose up
        player_input.yaw = self.controller.yaw  # -1 for full left, 1 for full right
        player_input.roll = self.controller.roll  # -1 for roll left, 1 for roll right
        player_input.jump = self.controller.jump  # true if you want to press the jump button
        player_input.boost = self.controller.boost  # true if you want to press the boost button
        player_input.handbrake = self.controller.handbrake  # true if you want to press the handbrake button
        return player_input

    @property
    def car(self) -> Car:
        """"Get the car from the world model.

        :return: The Car object corresponding to this car.
        :rtype: Car
        """
        return self.world.cars[self.index]

    def flush_actions(self):
        """ Removes all the items from the stack"""
        self.player_stack = []
        self.gosling_wrapper.flush_actions()

    def _step_base_player(self, current_routine: BasePlayer) -> bool:
        self.controller = SimpleControllerState()
        self.controller, done = current_routine.step()
        return done

    def _step_gosling(self, current_routine: Type[BasePlayer]) -> bool:
        resulting_routine, done, flushed = self.gosling_wrapper.update(
            current_routine)  # Update and run gosling wrapper
        self.controller = self.gosling_wrapper.controller  # Set controller
        if resulting_routine is not None:
            if flushed:
                self.player_stack = resulting_routine
            else:
                self.player_stack = self.player_stack[:-1] + resulting_routine
        elif flushed:
            self.player_stack = []
        return done
