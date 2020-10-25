from rlbot.agents.base_agent import SimpleControllerState


class BaseMechanic:
    def __init__(self, agent, rendering_enabled=False):
        self.controls = SimpleControllerState()
        self.agent = agent
        self.rendering_enabled = rendering_enabled
        self.finished = False
        self.failed = False

    def get_controls(self, *args) -> SimpleControllerState:
        raise NotImplementedError
