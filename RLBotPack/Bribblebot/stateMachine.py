

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from state.dribble import Dribble
from state.state import State
from state.test import Test

class StateMachine: 

    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self.currentState = None


    def tick(self, packet: GameTickPacket) -> SimpleControllerState:
        self.stateChanged = False

        if self.currentState == None:
            self.selectState(packet)

        #print(type(self.currentState).__name__)

        if not self.currentState.tick(packet):
            if not self.stateChanged:
                self.selectState(packet)
            assert self.currentState.tick(packet), "State exited without doing tick"

        return self.currentState.controller




    def selectState(self, packet: GameTickPacket):
        # if packet.game_ball.physics.location.z < 100:
        #     self.currentState = Test(self.agent)
        # else:
        self.currentState = Dribble(self.agent)

    def changeStateMidTick(self, state: State):
        self.currentState = state(self.agent)
        self.stateChanged = True



