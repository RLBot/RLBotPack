import os

from rlbot.agents.base_agent import BOT_CONFIG_AGENT_HEADER
from rlbot.agents.base_independent_agent import BaseIndependentAgent
from rlbot.botmanager.helper_process_request import HelperProcessRequest
from rlbot.parsing.custom_config import ConfigObject


class ScratchBot(BaseIndependentAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.port: int = None
        self.spawn_browser: bool = False
        self.sb3file: str = None
        self.headless: bool = False

    def get_helper_process_request(self):
        file = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scratch_manager.py'))
        self.logger.info(self.sb3file)
        key = 'scratch_helper' + (self.sb3file or '') + str(self.port)
        options = {
            'port': self.port,
            'spawn_browser': self.spawn_browser,
            'sb3-file': self.sb3file,
            'headless': self.headless
        }
        return HelperProcessRequest(file, key, options=options)

    def run_independently(self, terminate_request_event):
        pass

    def load_config(self, config_header):
        self.port = config_header.getint('port')
        self.spawn_browser = config_header.getint('spawn_browser')
        self.sb3file = config_header.getpath('sb3file')
        self.headless = config_header.getboolean('headless')

    @staticmethod
    def create_agent_configurations(config: ConfigObject):
        params = config.get_header(BOT_CONFIG_AGENT_HEADER)
        params.add_value('port', int, default=42008,
                         description='Port to use for websocket communication')
        params.add_value('spawn_browser', bool, default=False,
                         description='True if we should automatically open google chrome to the scratch page.')
        params.add_value('sb3file', str, default=None,
                         description='Location of the scratch .sb3 file to load automatically')
        params.add_value('headless', bool, default=False,
                         description='If true, bot will run automatically with no visible web browser')
