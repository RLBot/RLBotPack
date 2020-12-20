import random

from rlbot.agents.base_agent import SimpleControllerState
from rlbot.utils.game_state_util import GameState, BallState, Physics, CarState

from utility.info import Ball
from utility.vec import Vec3, normalize, Mat33, looking_in_dir

CAR_POS = Vec3(z=1350)
BALL_OFFSET = 200
DURATION = 4
ANTI_GRAV = Vec3(z=65)


class AerialControllerTest:

    def __init__(self):
        self.next_test = 0
        self.ball_pos = Vec3(z=Ball.RADIUS)

    def exec(self, bot) -> SimpleControllerState:

        if bot.info.time > 10 and bot.info.time > self.next_test:
            self.next_test = bot.info.time + DURATION

            dir = Vec3(
                random.random() - 0.5,
                random.random() - 0.5,
                random.random() - 0.5
            )
            self.ball_pos = CAR_POS + normalize(dir) * BALL_OFFSET

        bot.set_game_state(GameState(
            ball=BallState(Physics(location=self.ball_pos.to_desired_vec(), velocity=ANTI_GRAV.to_desired_vec())),
            cars={bot.index: CarState(physics=Physics(location=CAR_POS.to_desired_vec(), velocity=ANTI_GRAV.to_desired_vec()))}
        ))

        target_rot = looking_in_dir(self.ball_pos - CAR_POS)

        return bot.fly.align(bot, target_rot)
