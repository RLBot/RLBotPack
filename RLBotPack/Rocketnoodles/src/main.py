import configparser
import os
import pathlib
from strategy.drone import Drone
from physics.simulations.base_sim import BaseSim
from rlbot.agents.hivemind.python_hivemind import PythonHivemind
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.bot_input_struct import PlayerInput
from scenario.base_scenario import BaseScenario
from strategy.base_ccp import SharedInfo, BaseCoach
from typing import Dict
from world import World

# For dynamic importing - They are required!
from strategy.coaches import *
from scenario import *

CONFIG_FILE = os.path.join(pathlib.Path(__file__).parent.absolute(), 'settings', 'default.ini')


class TheHivemind(PythonHivemind, SharedInfo):
    """"The Rocket League entry point for the hivemind bot system."""

    def __init__(self, agent_metadata_queue, quit_event, options):

        # Read the config file
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        self.config = config

        # Check if testing mode is enabled
        self.test = config['general']['mode'] == "TEST"
        if self.test:
            self.scenario: BaseScenario = None

        self.coach: BaseCoach = None

        super().__init__(agent_metadata_queue, quit_event, options)

    def initialize_hive(self, packet: GameTickPacket) -> None:
        """"Initialization of the Hivemind. Set the Selector here.

        :param packet: GameTickPacket instance containing information about the environment.
        :type packet: GameTickPacket
        """

        # Setting information that is shared throughout the STP model and the simulations
        our_team_index = packet.game_cars[next(iter(self.drone_indices))].team  # Your team
        SharedInfo.world = World(packet, self.get_field_info())
        SharedInfo.drones = [Drone(f"Drone {i}", our_team_index, i) for i in self.drone_indices]
        BaseSim.world = SharedInfo.world
        BaseSim.agent = self

        # Reading selector dynamically from cfg file
        selector = globals()[self.config['strategy']['coach']]
        self.coach = selector()

        # Reading scenario dynamically from cfg file
        if self.test:
            scenario = globals()[self.config['test']['scenario']]
            self.scenario = scenario(packet)
            self.set_game_state(game_state=self.scenario.reset())

        self.logger.info('Noodle hivemind initialized')

    def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:
        """This is called once every game step.

        :param packet: object containing information about the environment.
        :type packet: GameTickPacket
        :return: Dictionary containing this team its drone indices as keys, and PlayerInput objects as values.
        :rtype packet: Dict[int, PlayerInput]
        """
        if self.test:
            new_game_state = self.scenario.reset_upon_condition(packet)
            if new_game_state:
                self.set_game_state(game_state=new_game_state)
                self.coach = globals()[self.config['strategy']['coach']]()
                return {drone.index: drone.get_player_input() for drone in self.drones}

        # Updates the world model with the current packet
        self.world.update_obs(packet, self.get_field_info())

        # Perform all steps in our STP model
        self.coach.step()

        # Return the inputs for each drone
        return {drone.index: drone.get_player_input() for drone in self.drones}
