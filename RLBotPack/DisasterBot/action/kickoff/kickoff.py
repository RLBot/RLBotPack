import math
from rlbot.agents.base_agent import SimpleControllerState
from action.base_action import BaseAction

from mechanic.drive_turn_face_target import DriveTurnFaceTarget
from mechanic.flip import Flip
from util.generator_utils import initialize_generator
from util.linear_algebra import norm, dot, normalize
from util.kickoff_utilities import get_kickoff_position
import numpy as np

from util.numerics import sign


class Kickoff(BaseAction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mechanic = DriveTurnFaceTarget(self.agent, self.rendering_enabled)
        self.flip = Flip(self.agent, self.rendering_enabled)
        self.kickoff = self.kickoff_generator()
        self.kickoff_type = 2

    def get_controls(self, game_data) -> SimpleControllerState:
        relative_ball = game_data.ball.location - game_data.my_car.location
        if norm(relative_ball) < 800:
            if self.flip.finished:
                self.flip = Flip(self.agent, self.rendering_enabled)
            self.controls = self.flip.get_controls(game_data.my_car, relative_ball)
        else:
            self.controls = self.kickoff.send(game_data)

        ball_loc = game_data.ball.location
        kickoff = math.sqrt(ball_loc[0] ** 2 + ball_loc[1] ** 2) < 1

        self.finished = not kickoff

        return self.controls

    @initialize_generator
    def kickoff_generator(self):
        game_data = yield

        while True:
            if self.agent.game_data.kickoff_pause:
                self.kickoff_type = get_kickoff_position(self.agent.game_data.my_car.location)

            relative_ball = game_data.ball.location - game_data.my_car.location

            if self.kickoff_type == 0:  # wide kickoff
                offset = np.array([100, 0, 0]) * sign(relative_ball[0])
            else:
                offset = np.array([50, 0, 0]) * sign(relative_ball[0])

            if game_data.my_car.boost > 15 or norm(relative_ball) < 2200:
                controls = self.mechanic.get_controls(game_data.my_car, game_data.ball.location + offset)
                controls.throttle = 1
                controls.boost = True
                game_data = yield controls
            else:
                flip = Flip(self.agent, self.rendering_enabled)
                while not flip.finished:
                    controls = flip.get_controls(game_data.my_car, relative_ball)
                    if dot(game_data.my_car.rotation_matrix[:, 0], normalize(relative_ball)) > 0.5:
                        controls.boost = True
                    game_data = yield controls
