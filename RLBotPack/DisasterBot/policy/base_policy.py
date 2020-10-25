from action.base_action import BaseAction


class BasePolicy:
    def __init__(self, agent, rendering_enabled=False):
        self.agent = agent
        self.rendering_enabled = rendering_enabled

    def get_controls(self, game_data):
        return self.get_action(game_data).get_controls(game_data)

    def get_action(self, game_data) -> BaseAction:
        raise NotImplementedError
