from rlbot.agents.base_agent import SimpleControllerState

from action.base_action import BaseAction
from util.boost_utils import closest_available_boost
from mechanic.drive_navigate_boost import DriveNavigateBoost


class CollectBoost(BaseAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mechanic = DriveNavigateBoost(self.agent, self.rendering_enabled)

    def get_controls(self, game_data) -> SimpleControllerState:

        car = game_data.my_car
        boost_pads = game_data.boost_pads[game_data.boost_pads["is_full_boost"]]
        boost_pad = closest_available_boost(car.location + car.velocity / 2, boost_pads)

        if boost_pad is None:
            # All boost pads are inactive.
            self.failed = True
            return self.controls

        self.controls = self.mechanic.get_controls(game_data.my_car, game_data.boost_pads, boost_pad["location"])

        if car.boost == 100:
            self.finished = True

        return self.controls

    def is_valid(self, game_data):
        return len(game_data.boost_pads["is_active"]) > 0
