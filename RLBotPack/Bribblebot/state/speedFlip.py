



from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from rlbot.utils.game_state_util import GameState, BallState, CarState, Physics, Vector3, Rotator, GameInfoState
from rlbot.utils.structures.quick_chats import QuickChats


from state.state import State
import math
import random

from rlutilities.simulation import Ball, Field, Game
from rlutilities.linear_algebra import vec3, norm, atan2, rotate2


DEBUG = False


class SpeedFlip(State):
	def __init__(self, agent: BaseAgent):
		super().__init__(agent)

		self.speedFlipTarget = None
		self.speedFlipDirection = None # 1 for left, -1 for right

		self.speedFlipState = 0
		self.lastActionTick = None
		self.lastSpeed = 0
		self.lastAngle = 0
		self.speedFlipMaxTurnTicks = 22

		
	def tick(self, packet: GameTickPacket) -> bool:

		speed = norm(self.agent.car.velocity)
		angle = atan2(self.agent.car.velocity)

		if self.lastActionTick == None:
			self.lastActionTick = self.agent.currentTick
		delta = self.agent.currentTick - self.lastActionTick

		# if DEBUG:
		# 	print(self.speedFlipState)

		# 1. turn away from direction
		if self.speedFlipState == 0:
			if self.speedFlipTarget is not None:
				carAngle = -atan2(self.agent.car.forward())
				carToTargetAngle = -atan2(rotate2(self.speedFlipTarget - self.agent.car.position, carAngle))
			else:
				carToTargetAngle = 0
			if delta < self.speedFlipMaxTurnTicks and abs(carToTargetAngle) < 0.27:
				if delta == 0 and self.speedFlipDirection == None:
					self.speedFlipDirection = math.copysign(1, carToTargetAngle + (random.random() - 0.5) / 10000)
				
				self.controller.boost = True
				self.controller.throttle = 1
				self.controller.steer = 0.65 * self.speedFlipDirection
				self.controller.yaw = 1 * self.speedFlipDirection
				self.controller.jump = False

			else:
				if self.speedFlipDirection == None:
					self.speedFlipDirection = math.copysign(1, carToTargetAngle + (random.random() - 0.5) / 10000)
				self.speedFlipState = 1
				self.lastActionTick = self.agent.currentTick

		# 2. longest possible jump, counter pitch
		elif self.speedFlipState == 1:
			if delta < 8:
				self.controller.jump = True
				self.controller.pitch = 1
				self.controller.yaw = 1 * self.speedFlipDirection
			else:
				self.speedFlipState = 2
				
		# 3. dodge, and immediate counter pitch
		if self.speedFlipState == 2:
			self.controller.jump = False
			self.speedFlipState = 3
		elif self.speedFlipState == 3:
			self.controller.jump = True
			self.controller.pitch = -1
			self.controller.roll = -.8 * self.speedFlipDirection
			self.controller.yaw = 0
			self.speedFlipState = 4
			self.lastActionTick = self.agent.currentTick

			
			self.lastSpeed = -speed
			self.lastAngle = angle

		elif self.speedFlipState == 4:
			if delta < 30:
				self.controller.jump = False
				self.controller.pitch = 1
				self.controller.roll = -1 * self.speedFlipDirection
				self.controller.yaw = -1 * self.speedFlipDirection
				
				if self.lastSpeed < 0:
					self.lastSpeed = -self.lastSpeed
				elif self.lastSpeed != 9000:
					self.lastSpeed = 9000

			else:
				self.speedFlipState = 5
				self.lastActionTick = self.agent.currentTick

		# # counter roll aswell
		if self.speedFlipState == 5:
			if delta < 20:
				self.controller.roll = 1 * self.speedFlipDirection
			else:
				self.speedFlipState = 6
				self.lastActionTick = self.agent.currentTick
				
		# when on ground, stop pitch, signal that its finished
		if self.speedFlipState == 6:
			if self.agent.car.on_ground:
				self.controller.roll = 0
				self.controller.pitch = 0
				# if delta < 95:
				#     self.controller.handbrake = True
				# else:
				#     self.controller.handbrake = False
				self.speedFlipState = 7
		if self.speedFlipState == 7:
			return False

		return True
