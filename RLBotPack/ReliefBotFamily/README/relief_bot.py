import os

from rlbot.agents.base_agent import BOT_CONFIG_AGENT_HEADER
from rlbot.agents.executable_with_socket_agent import ExecutableWithSocketAgent
from rlbot.botmanager.helper_process_request import HelperProcessRequest
from rlbot.parsing.custom_config import ConfigHeader, ConfigObject

ACTION_SERVER_PORT = 4687


class ReliefBot(ExecutableWithSocketAgent):

    def get_port(self) -> int:
        return 22868

    def __init__(self, name, team, index):
        super().__init__(name, team, index)

    def load_config(self, config_header: ConfigHeader):
        self.executable_path = config_header.getpath('java_executable_path')
        self.logger.info("Java executable is configured as {}".format(self.executable_path))

    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value('java_executable_path', str, default=None,
                         description='Relative path to the executable that runs java.')

    def get_helper_process_request(self):
        if self.is_executable_configured():
            return HelperProcessRequest(python_file_path=None, key=__file__ + str(self.get_port()),
                                        executable=self.executable_path, exe_args=[str(self.get_port()), f'--server.port={ACTION_SERVER_PORT}'],
                                        current_working_directory=os.path.dirname(self.executable_path))
        return None
