from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.orientation import Orientation
from util.vec import Vec3
import util.const

from state.state import State
import math

from rlutilities.simulation import Ball, Field, Game
from rlutilities.linear_algebra import vec3


class CelebrationPostGame(State):
    def __init__(self, agent: BaseAgent):
        super().__init__(agent)


    def tick(self, packet: GameTickPacket) -> bool:

        #print(f"matchend:\t{packet.game_info.is_match_ended}\tactive:\t{packet.game_info.is_round_active}\tkickoff:\t{packet.game_info.is_kickoff_pause}\tovertime:\t{packet.game_info.is_overtime}\tballCenter:\t{packet.game_ball.physics.location.x == 0 and packet.game_ball.physics.location.y == 0}\ttimeLeft:\t{packet.game_info.game_time_remaining}")

        time = -packet.game_info.game_time_remaining - 3.4
        # print(round(time,2))

        if time < 0:
            pass
        elif time < .1:
            self.controller.jump = True
            self.controller.roll = -1
            self.controller.yaw = -1
        elif time < .35:
            self.controller.jump = False
        elif time < 1.5:
            self.controller.roll = 0
        elif time < 1.6:
            self.controller.yaw = 0
            self.controller.pitch = 1
        elif time < 1.75:
            self.controller.pitch = 0
            self.controller.boost = True
        else:
            self.controller.roll = 1

        return True