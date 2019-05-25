import os
import time

import psutil
from py4j.java_gateway import GatewayParameters
from py4j.java_gateway import JavaGateway
from rlbot.agents.base_agent import BaseAgent
from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.logging_utils import get_logger
from rlbot.utils.structures import game_interface
from rlbot.utils.structures.game_data_struct import GameTickPacket


class ReliefBotPy(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.gateway = None
        self.javaInterface = None
        self.logger = get_logger('ReliefBotPy' + str(self.index))
        self.is_retired = False
        self.port = self.read_port_from_file()

    def get_output(self, game_tick_packet: GameTickPacket) -> SimpleControllerState:
        java_output = self.javaInterface.getOutput(self.index, game_tick_packet.game_info.seconds_elapsed)
        return self.convert_output_to_v4(java_output)

    def read_port_from_file(self):
        try:
            location = self.get_port_file_path()

            with open(location, "r") as portFile:
                return int(portFile.readline().rstrip())

        except ValueError:
            self.logger.warn("Failed to parse port file!")
            raise

    def get_port_file_path(self):
        # Look for a port.cfg file in the same directory as THIS python file.
        return os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), 'port.cfg'))

    def initialize_agent(self):

        initialized = False

        while not initialized:
            # Continuously make sure the java interface is started and the bot is registered.
            # These functions can be called repeatedly without any bad effects.
            # This is useful for re-engaging the java server if it gets restarted during development.
            try:
                self.init_py4j_stuff()
                self.javaInterface.ensureDllInitialized(game_interface.get_dll_location())
                self.javaInterface.registerPyAdapter(self.index, self.name, self.team)
                initialized = True
            except Exception as e:
                self.logger.warn(str(e))
                time.sleep(1)


    def retire(self):
        try:
            # Shut down the whole java process, because currently java is clumsy with the interface dll
            # and cannot really survive a restart of the python framework.
            self.javaInterface.shutdown()
        except Exception as e:
            self.logger.warn(str(e))
        self.is_retired = True

    def init_py4j_stuff(self):
        self.logger.info("Connecting to Java Gateway on port " + str(self.port))
        self.gateway = JavaGateway(gateway_parameters=GatewayParameters(auto_convert=True, port=self.port))
        self.javaInterface = self.gateway.entry_point
        self.logger.info("Connection to Java successful!")

    def read_port_from_file(self):
        try:
            location = self.get_port_file_path()

            with open(location, "r") as portFile:
                return int(portFile.readline().rstrip())

        except ValueError:
            self.logger.warn("Failed to parse port file!")
            raise

    def get_extra_pids(self):
        """
        Gets the list of process ids that should be marked as high priority.
        :return: A list of process ids that are used by this bot in addition to the ones inside the python process.
        """
        while not self.is_retired:
            for proc in psutil.process_iter():
                for conn in proc.connections():
                    if conn.laddr.port == self.port:
                        self.logger.debug('py4j server for {} appears to have pid {}'.format(self.name, proc.pid))
                        return [proc.pid]
            time.sleep(1)
