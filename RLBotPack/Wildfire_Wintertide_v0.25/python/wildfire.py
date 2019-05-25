import os

from rlbot.agents.base_agent import BOT_CONFIG_AGENT_HEADER
from rlbot.agents.base_java_agent import BaseJavaAgent
from rlbot.parsing.custom_config import ConfigHeader, ConfigObject

class JavaExample(BaseJavaAgent):
    def get_port_file_path(self):
        # Look for a port.cfg file in the same directory as THIS python file.
        return os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), 'port.cfg'))

    def load_config(self, config_header: ConfigHeader):
        self.java_executable_path = config_header.getpath('java_executable_path')
        self.logger.info("Java executable is configured as {}".format(self.java_executable_path))

    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value('java_executable_path', str, default=None,
                         description='Relative path to the executable that runs java.')
