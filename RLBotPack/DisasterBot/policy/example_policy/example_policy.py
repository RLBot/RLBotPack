import math

from policy.base_policy import BasePolicy
from action.base_action import BaseAction

from action.collect_boost import CollectBoost
from action.kickoff import Kickoff
from action.hit_ground_ball import HitGroundBall

from skeleton.util.structure import GameData
from util.generator_utils import initialize_generator

from typing import Generator


class ExamplePolicy(BasePolicy):
    def __init__(self, agent, rendering_enabled=True):
        super(ExamplePolicy, self).__init__(agent, rendering_enabled)
        self.kickoff_action = Kickoff(agent, rendering_enabled)
        self.action_loop = self.create_action_loop()

    def get_action(self, game_data: GameData) -> BaseAction:
        ball_loc = game_data.ball.location
        kickoff = math.sqrt(ball_loc[0] ** 2 + ball_loc[1] ** 2) < 1

        if kickoff:
            # reset the action loop
            self.action_loop = self.create_action_loop()
            return self.kickoff_action
        else:
            return self.action_loop.send(game_data)

    @initialize_generator
    def create_action_loop(self) -> Generator[BaseAction, GameData, None]:
        game_data = yield

        while True:
            # choose action to do
            if game_data.my_car.boost > 20:
                action = HitGroundBall(self.agent, self.rendering_enabled)
            else:
                action = CollectBoost(self.agent, self.rendering_enabled)

            # use action until it is finished
            while not action.finished and not action.failed:
                game_data = yield action
