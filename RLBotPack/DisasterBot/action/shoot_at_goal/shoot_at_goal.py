from rlbot.agents.base_agent import SimpleControllerState

from action.base_action import BaseAction
from mechanic.drive_navigate_boost import DriveNavigateBoost
from mechanic.jumping_shot import JumpingShot
from skeleton.util.structure import GameData
from skeleton.util.structure.dtypes import dtype_full_boost
from util.ball_utils import get_ground_ball_intercept_state
from util.linear_algebra import norm, flatten, dot
import numpy as np

from util.kickoff_utilities import calc_target_dir


class ShootAtGoal(BaseAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mechanic = DriveNavigateBoost(self.agent, self.rendering_enabled)
        self.jump_shot = None

    def get_controls(self, game_data: GameData) -> SimpleControllerState:
        target_loc, target_dt, target_vel = get_ground_ball_intercept_state(game_data)
        target_dir = calc_target_dir(game_data, target_loc, target_vel)

        if self.jumpshot_valid(game_data, target_loc, target_dt, target_dir) and self.jump_shot is None:
            self.jump_shot = JumpingShot(
                self.agent, target_loc, target_dt - 0.1, game_data.game_tick_packet, self.rendering_enabled,
            )

        if self.jump_shot is not None:
            controls = self.jump_shot.get_controls(game_data.my_car, game_data.game_tick_packet)
            self.finished = self.jump_shot.finished
            self.failed = self.jump_shot.failed
            return controls

        goal_pad = np.zeros(1, dtype_full_boost)
        goal_pad["location"] = flatten(game_data.own_goal.location)
        goal_pad["timer"] = -np.inf
        boost_pads = np.concatenate([game_data.boost_pads, goal_pad])

        controls = self.mechanic.get_controls(
            game_data.my_car, boost_pads, target_loc, target_dt, target_dir.astype(float),
        )

        self.finished = self.mechanic.finished
        self.failed = self.mechanic.failed

        return controls

    def jumpshot_valid(self, game_data, target_loc, target_dt, target_dir) -> bool:
        best_dt = (target_loc[2] - game_data.my_car.location[2]) / 300
        future_projection = game_data.my_car.location + game_data.my_car.velocity * target_dt
        difference = future_projection - target_loc
        difference[2] = 0
        return (
            norm(difference) < 150
            and target_dt - best_dt < 0.1
            and dot(target_loc - game_data.my_car.location, target_dir) > 0
        )

    def is_valid(self, game_data):
        return True
