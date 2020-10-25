from rlbot.agents.base_agent import SimpleControllerState

from action.base_action import BaseAction
from mechanic.drive_navigate_boost import DriveNavigateBoost
from skeleton.util.structure import GameData
from util.linear_algebra import normalize, norm, dot


class ShadowBall(BaseAction):
    def __init__(self, agent, rendering_enabled, distance):
        super().__init__(agent, rendering_enabled)
        self.mechanic = DriveNavigateBoost(agent, rendering_enabled)
        self.distance = distance

    def get_controls(self, game_data: GameData) -> SimpleControllerState:
        dt = norm(game_data.own_goal.location - game_data.ball.location) / 3000
        ball_location = game_data.ball_prediction[int(60 * dt)]["physics"]["location"]
        ball_velocity = game_data.ball_prediction[int(60 * dt)]["physics"]["velocity"]
        target_loc = normalize(game_data.own_goal.location - ball_location) * self.distance + ball_location
        up = game_data.my_car.rotation_matrix[:, 2]
        target_loc = target_loc - dot(target_loc - game_data.my_car.location, up) * up
        target_dir = ball_velocity.astype(float)

        controls = self.mechanic.get_controls(game_data.my_car, game_data.boost_pads, target_loc, dt, target_dir)

        self.finished = self.mechanic.finished
        self.failed = self.mechanic.failed

        return controls

    def is_valid(self, game_data):
        return True
