from rlbot.agents.base_agent import BOT_CONFIG_AGENT_HEADER
from rlbot.agents.executable_with_socket_agent import ExecutableWithSocketAgent
from rlbot.parsing.custom_config import ConfigHeader, ConfigObject


class JavaExample(ExecutableWithSocketAgent):
    def get_port(self) -> int:
        return 17357

    def load_config(self, config_header: ConfigHeader):
        self.executable_path = config_header.getpath('java_executable_path')
        self.logger.info("Java executable is configured as {}".format(self.executable_path))

    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value('java_executable_path', str, default=None,
                         description='Relative path to the executable that runs java.')
