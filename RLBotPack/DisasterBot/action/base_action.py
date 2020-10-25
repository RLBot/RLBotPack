from rlbot.agents.base_agent import SimpleControllerState


class BaseAction:
    def __init__(self, agent, rendering_enabled=False):
        self.agent = agent
        self.rendering_enabled = rendering_enabled
        self.controls = SimpleControllerState()
        self.finished = False
        self.failed = False

    def get_controls(self, game_data) -> SimpleControllerState:
        raise NotImplementedError
