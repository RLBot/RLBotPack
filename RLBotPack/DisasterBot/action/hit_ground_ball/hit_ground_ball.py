from rlbot.agents.base_agent import SimpleControllerState

from action.base_action import BaseAction
from mechanic.drive_arrive_in_time import DriveArriveInTime
from util.ball_utils import get_ground_ball_intercept_state


class HitGroundBall(BaseAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mechanic = DriveArriveInTime(self.agent, self.rendering_enabled)
        self.target_loc = None
        self.target_time = None

    def get_controls(self, game_data) -> SimpleControllerState:

        if self.target_loc is None or True:
            # remove "or True" to test the accuracy without recalculating each tick.
            self.target_loc, target_dt = get_ground_ball_intercept_state(game_data)
            self.target_time = game_data.time + target_dt

        target_dt = self.target_time - game_data.time
        self.controls = self.mechanic.get_controls(game_data.my_car, self.target_loc, target_dt)

        self.finished = self.mechanic.finished
        self.failed = self.mechanic.failed

        return self.controls

    def is_valid(self, game_data):
        return True
