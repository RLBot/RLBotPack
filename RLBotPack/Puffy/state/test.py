from rlbot.agents.base_agent import BaseAgent
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState


from util.orientation import Orientation
from util.vec import Vec3
import util.const

from state.state import State
# from state.dribble import getTargetBall
# import math


# normalSpeed = 1409
# boostSpeed = 2299

class Test(State):
    def __init__(self, agent: BaseAgent):
        super().__init__(agent)
        self.didReset = False


    def tick(self, packet: GameTickPacket) -> bool:
        
#         if self.didReset:
#             return False

#         location, velocity, angle = getTargetBall(self.agent, packet, Vec3())
#         newVelocity = Vector3(velocity.x, velocity.y, velocity.z)

#         newCarLocation = Vector3(location.x, location.y, 25)
#         carState = CarState(Physics(location=newCarLocation, velocity=newVelocity, rotation=Rotator(0, -angle, 0)))
        
#         newBallLocation = Vector3(location.x, location.y, 150)
#         ballState = BallState(Physics(location=newBallLocation, velocity=newVelocity))

#         gameState = GameState(ball=ballState, cars={self.agent.index: carState})
#         self.agent.set_game_state(gameState)
#         self.didReset = True

        return True

