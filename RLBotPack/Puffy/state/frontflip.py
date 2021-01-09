from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.orientation import Orientation
from util.vec import Vec3
import util.const

from state.state import State
import math



class Frontflip(State):
    def __init__(self, agent: BaseAgent): 
        super().__init__(agent)
        self.startTick = 0
        self.state = 0


    def tick(self, packet: GameTickPacket) -> bool:

        if self.state > 60:
            return False





        if self.startTick == 0:
            self.startTick = self.agent.currentTick

        ticksElapsed = self.agent.currentTick - self.startTick
            

        jumpTick = 7
        if self.state == 0:
            if ticksElapsed >= jumpTick:
                self.state = 1
            else:
                self.controller.jump = True
        
        if self.state == 1:
            if self.controller.jump: # set it to false for one input frame
                self.controller.jump = False
            else:
                self.state = 2
        if self.state == 2:
            self.state = 3
            self.controller.jump = True
        if self.state > 2:
            self.state += 1

        self.controller.pitch = -1
        self.controller.throttle = 1

        #print(f"{ticksElapsed}\t{self.controller.jump}")
        return True
