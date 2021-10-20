import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats
from util.orientation import Orientation
from util.vec import Vec3
import util.const

from rlutilities.linear_algebra import euler_to_rotation, dot, transpose, look_at, vec2, vec3, norm, normalize, angle_between, orthogonalize
from rlutilities.simulation import Ball, Field, Game, Car
from rlutilities.mechanics import ReorientML


import sys
from stateMachine import StateMachine

IGNORE_LIST = ["Kamael"]


class BribbleBot(BaseAgent):

	def is_hot_reload_enabled(self):
		return False

	def initialize_agent(self):
		# This runs once before the bot starts up
		self.controllerState = SimpleControllerState()
		self.stateMachine = StateMachine(self)
		
		self.lastTime = 0
		self.realLastTime = 0
		self.doneTicks = 0
		self.skippedTicks = 0
		self.ticksThisPacket = 0
		self.FPS = 120
		self.lastQuickChatTime = 0
		self.secondMessage = None
		self.currentTick = 0
		self.firstTpsReport = True

		self.game = Game()
		self.game.set_mode("soccar")
		self.car = self.game.cars[self.index]
		self.reorientML = ReorientML(self.car)

		self.lastJumpTick = -math.inf
		self.maxDodgeTick = 0
		self.jumpReleased = True
		self.lastDodgeTick = -math.inf
		self.lastController = SimpleControllerState()


	def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
		# self.renderer.begin_rendering()
		self.packet = packet

		self.handleTime()

		self.game.read_game_information(packet, self.get_rigid_body_tick(), self.get_field_info())


		ballY = packet.game_ball.physics.location.y

		if abs(ballY) > 5120+60 and packet.game_info.seconds_elapsed - self.lastQuickChatTime > 15:
			teamDirection = 1 if packet.game_ball.latest_touch.team == 0 else -1
			firstByToucher = True
			if ballY * teamDirection > 0:
				if packet.game_ball.latest_touch.team == packet.game_cars[self.index].team:
					firstMessage, secondMessage = QuickChats.Compliments_NiceShot, QuickChats.Compliments_Thanks
					firstByToucher = False
				else:
					firstMessage, secondMessage = QuickChats.Apologies_Whoops, QuickChats.Apologies_NoProblem
			
			else:
				if packet.game_ball.latest_touch.team == packet.game_cars[self.index].team:
					firstMessage, secondMessage = QuickChats.Compliments_WhatASave, QuickChats.Apologies_NoProblem
					firstByToucher = False
				else:
					firstMessage, secondMessage = QuickChats.Compliments_WhatASave, QuickChats.Reactions_Savage

			bribbleBots = []
			latestTouchIsBribble = False
			for carIndex in range(packet.num_cars):
				car = packet.game_cars[carIndex]
				if car.team == self.team and "Bribblebot" in car.name:
					bribbleBots.append(carIndex)
					if packet.game_ball.latest_touch.player_index == carIndex:
						latestTouchIsBribble = True
			
			if len(bribbleBots) == 1:
				self.send_quick_chat(QuickChats.CHAT_EVERYONE, firstMessage)
				self.secondMessage = secondMessage
			else:
				sendFirst = packet.game_ball.latest_touch.player_index == self.index or (not latestTouchIsBribble and self.index == min(bribbleBots))
				if not sendFirst ^ firstByToucher:
					self.send_quick_chat(QuickChats.CHAT_EVERYONE, firstMessage)
				else:
					self.secondMessage = secondMessage


			self.lastQuickChatTime = packet.game_info.seconds_elapsed


		elif packet.game_info.seconds_elapsed - self.lastQuickChatTime > 0.2 and self.secondMessage != None:
			self.send_quick_chat(QuickChats.CHAT_EVERYONE, self.secondMessage)
			self.secondMessage = None

		self.stateMachine.tick(packet)
		self.trackJump(self.stateMachine.currentState.controller)

		# self.renderer.end_rendering()
		return self.stateMachine.currentState.controller






	def trackJump(self, controller: SimpleControllerState):
		
		if controller.jump and not self.lastController.jump and self.car.on_ground and self.currentTick - self.lastJumpTick > 28:
			self.lastJumpTick = self.currentTick
			self.jumpReleased = False

		if self.car.on_ground:
			self.maxDodgeTick = math.inf
			self.lastJumpTick = -math.inf
			self.lastDodgeTick = -math.inf
		elif self.lastController.jump and self.currentTick - self.lastJumpTick > 28:
			if not controller.jump:
				self.maxDodgeTick = self.currentTick + 1.25 * 120
			elif self.lastJumpTick == -math.inf:
				self.maxDodgeTick = math.inf
			else:
				self.maxDodgeTick = self.lastJumpTick + 1.45 * 120

		if not self.car.on_ground and controller.jump and not self.car.double_jumped and self.currentTick <= self.maxDodgeTick:
			self.lastDodgeTick = self.currentTick
			

		if not self.jumpReleased and not controller.jump:
			self.jumpReleased = True

		self.lastController = controller






	def handleTime(self):
		# this is the most conservative possible approach, but it could lead to having a "backlog" of ticks if seconds_elapsed
		# isnt perfectly accurate.
		if not self.lastTime:
			self.lastTime = self.packet.game_info.seconds_elapsed
		else:
			if self.realLastTime == self.packet.game_info.seconds_elapsed:
				return

			if int(self.lastTime) != int(self.packet.game_info.seconds_elapsed):
				# if self.skippedTicks > 0:
				print(f"did {self.doneTicks}, skipped {self.skippedTicks}")
				if self.firstTpsReport or self.packet.game_ball.physics.location.x == 0 and self.packet.game_ball.physics.location.y == 0:
					self.firstTpsReport = False
				elif self.doneTicks < 110:
					self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Excuses_Lag)
				self.skippedTicks = self.doneTicks = 0

			ticksPassed = round(max(1, (self.packet.game_info.seconds_elapsed - self.lastTime) * self.FPS))
			self.lastTime = min(self.packet.game_info.seconds_elapsed, self.lastTime + ticksPassed)
			self.realLastTime = self.packet.game_info.seconds_elapsed
			self.currentTick += ticksPassed
			if ticksPassed > 1:
				# print(f"Skipped {ticksPassed - 1} ticks!")
				self.skippedTicks += ticksPassed - 1
			self.doneTicks += 1