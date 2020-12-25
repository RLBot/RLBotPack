from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from state.recover import Recover
import math


from rlutilities.simulation import Ball, Field, Game, Car
from rlutilities.linear_algebra import vec2, vec3, mat3, euler_to_rotation, look_at, norm, normalize, angle_between, dot, flatten



from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState





class HalfFlip(Recover):
	def __init__(self, agent: BaseAgent, forceBackFlip = False, waitFinish = False, *args):
		if forceBackFlip:
			forceLandDirection = flatten(agent.car.forward())
		else:
			forceLandDirection = None
		super().__init__(agent, forceLandDirection, *args)
		
		self.recoveryActive = False
		self.halfFlipStartTick = None
		self.halfFlipFinished = False
		self.forceBackFlip = forceBackFlip
		self.waitFinish = waitFinish

	def tick(self, packet: GameTickPacket) -> bool:
		if super().tick(packet):
			return True
		elif self.recoveryActive:
			return False

		self.controller.steer = 0
		self.controller.throttle = -1
		self.controller.boost = False
		self.controller.pitch = 1
		self.controller.yaw = 0
		self.controller.roll = 0
		if self.halfFlipStartTick == None:
			self.halfFlipStartTick = self.agent.currentTick
		if self.agent.currentTick < self.halfFlipStartTick + (10 if self.forceBackFlip else 7):
			self.controller.jump = True
		elif not self.halfFlipFinished:
			if self.controller.jump == True:
				self.controller.jump = False
			else:
				self.controller.jump = True
				self.halfFlipFinished = True
		else:
			if self.agent.currentTick > self.halfFlipStartTick + (80 if self.forceBackFlip else 10):# or not self.forceBackFlip:
				self.recoveryActive = True

		return True



