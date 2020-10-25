import math

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats
from util.orientation import Orientation
from util.vec import Vec3
import util.const

import sys
from stateMachine import StateMachine


class BribbleBot(BaseAgent):

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
		self.tick = 0
		self.firstTpsReport = True

	def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
		self.packet = packet

		self.handleTime()

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


		return self.stateMachine.tick(packet)






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
				if self.firstTpsReport:
					self.firstTpsReport = False
				elif self.doneTicks < 110:
					self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Excuses_Lag)
				self.skippedTicks = self.doneTicks = 0

			ticksPassed = round(max(1, (self.packet.game_info.seconds_elapsed - self.lastTime) * self.FPS))
			self.lastTime = min(self.packet.game_info.seconds_elapsed, self.lastTime + ticksPassed)
			self.realLastTime = self.packet.game_info.seconds_elapsed
			self.tick += ticksPassed
			if ticksPassed > 1:
				# print(f"Skipped {ticksPassed - 1} ticks!")
				self.skippedTicks += ticksPassed - 1
			self.doneTicks += 1