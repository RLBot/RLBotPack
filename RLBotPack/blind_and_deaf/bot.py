from typing import List
from random import randint
from dataclasses import dataclass

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from rlutilities.simulation import Game
from rlutilities.linear_algebra import vec3

from hover import Hover

HOVER_IDLE_HEIGHT = 300
HOVER_IDLE_Y = 4800
HOVER_MIN_HEIGHT = 140
HOVER_MAX_HEIGHT = 1200
HOVER_MAX_SIDE = 1500
HOVER_TARGET_Y = 4800


def sign(x):
    return 1 if x >= 0 else -1

class MyBot(BaseAgent):

    def initialize_agent(self):
        # This runs once before the bot starts up
        self.controller_state = SimpleControllerState()

        self.info = Game(self.team)
        self.hover = Hover(self.info.cars[self.index], self.info)
        self.sign = 2 * self.team - 1  # 1 if orange, else -1

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.info.read_game_information(packet, self.get_field_info())

        ball_prediction = self.get_ball_prediction_struct()
        future_goal = self.find_future_goal(ball_prediction)
        if future_goal and not packet.game_info.is_kickoff_pause:
            target = future_goal
        else:
            target = vec3(0, HOVER_IDLE_Y * self.sign, HOVER_IDLE_HEIGHT)

        # render target
        self.renderer.begin_rendering("target")
        self.renderer.draw_rect_3d(target, 10, 10, True, self.renderer.cyan())
        self.renderer.end_rendering()

        # update controls
        self.hover.target = target
        self.hover.step(self.info.time_delta)
        self.controller_state = self.hover.controls

        return self.controller_state

    def find_future_goal(self, ball_prediction):
        for step in ball_prediction.slices[:ball_prediction.num_slices]:
            pos = step.physics.location
            if sign(pos.y) != self.sign:
                continue
            if abs(pos.y) > HOVER_TARGET_Y and abs(pos.x) < HOVER_MAX_SIDE and pos.z < HOVER_MAX_HEIGHT:
                return vec3(pos.x, pos.y, pos.z if pos.z > 100 else HOVER_MIN_HEIGHT)
        return None
